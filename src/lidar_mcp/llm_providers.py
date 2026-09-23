"""Local + cloud LLM provider layer for the lidar-mcp web backend.

Contracts follow WEBAPP_SOTA_STANDARDS.md section VI.10 (copy, do not
reinvent): provider cards, backend-only key handling, OpenAI-style SSE
streaming. Keys live in ``data/llm_keys.json`` (0600, gitignored) or env
(env wins). Keys never leave the server.
"""

from __future__ import annotations

import json
import logging
import os
import stat
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

PROBE_TIMEOUT_S = 3.0
CHAT_TIMEOUT_S = 120.0

LOCALS: list[dict[str, Any]] = [
    {"id": "ollama", "label": "Ollama", "port": 11434, "kind": "local"},
    {"id": "lmstudio", "label": "LM Studio", "port": 1234, "kind": "local"},
    {"id": "vllm", "label": "vLLM", "port": 8000, "kind": "local"},
]

CLOUDS: list[dict[str, Any]] = [
    {
        "id": "openai",
        "label": "OpenAI",
        "kind": "cloud",
        "base_url": "https://api.openai.com/v1",
        "key_env": "OPENAI_API_KEY",
        "models_url": "https://api.openai.com/v1/models",
    },
    {
        "id": "anthropic",
        "label": "Anthropic",
        "kind": "cloud",
        "base_url": "https://api.anthropic.com/v1",
        "key_env": "ANTHROPIC_API_KEY",
        "models_url": "",
    },
]

_ANTHROPIC_VERSION = "2023-06-01"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _keystore_path() -> Path:
    return _repo_root() / "data" / "llm_keys.json"


def _read_keystore() -> dict[str, str]:
    try:
        raw = _keystore_path().read_text(encoding="utf-8")
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_keystore(data: dict[str, str]) -> None:
    path = _keystore_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        logger.warning("Could not chmod keystore to 0600")


def get_key(provider_id: str) -> str:
    """Env wins, keystore is the fallback. Empty string when unconfigured."""
    for cloud in CLOUDS:
        if cloud["id"] == provider_id:
            env_val = os.environ.get(cloud["key_env"], "")
            if env_val:
                return env_val
            val = _read_keystore().get(provider_id, "")
            return val if isinstance(val, str) else ""
    return ""


def set_key(provider_id: str, api_key: str) -> dict[str, Any]:
    if not any(c["id"] == provider_id for c in CLOUDS):
        return {"success": False, "message": f"Unknown cloud provider: {provider_id}"}
    store = _read_keystore()
    store[provider_id] = api_key
    _write_keystore(store)
    logger.info("Stored API key for provider %s (length hidden)", provider_id)
    return {"success": True, "message": f"Key saved for {provider_id}"}


def delete_key(provider_id: str) -> dict[str, Any]:
    store = _read_keystore()
    store.pop(provider_id, None)
    _write_keystore(store)
    return {"success": True, "message": f"Key cleared for {provider_id}"}


async def _probe_local(client: httpx.AsyncClient, spec: dict[str, Any]) -> dict[str, Any]:
    base = f"http://127.0.0.1:{spec['port']}"
    detected = False
    models: list[str] = []
    loaded: list[str] = []
    try:
        if spec["id"] == "ollama":
            resp = await client.get(f"{base}/api/tags", timeout=PROBE_TIMEOUT_S)
            if resp.status_code == 200:
                detected = True
                models = [m.get("name", "") for m in resp.json().get("models", [])]
            try:
                ps = await client.get(f"{base}/api/ps", timeout=PROBE_TIMEOUT_S)
                if ps.status_code == 200:
                    loaded = [m.get("name", "") for m in ps.json().get("models", [])]
            except (httpx.HTTPError, ValueError):
                loaded = []
        else:
            resp = await client.get(f"{base}/v1/models", timeout=PROBE_TIMEOUT_S)
            if resp.status_code == 200:
                detected = True
                models = [m.get("id", "") for m in resp.json().get("data", [])]
    except httpx.HTTPError:
        detected = False
    return {
        "id": spec["id"],
        "label": spec["label"],
        "kind": "local",
        "base_url": base,
        "needs_key": False,
        "key_env": "",
        "configured": detected,
        "detected": detected,
        "models": [m for m in models if m],
        "loaded": [m for m in loaded if m],
    }


def list_providers_sync_shape(detected_locals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge local detection results with the cloud registry (no key bytes)."""
    out = [dict(d) for d in detected_locals]
    for cloud in CLOUDS:
        key = get_key(cloud["id"])
        out.append(
            {
                "id": cloud["id"],
                "label": cloud["label"],
                "kind": "cloud",
                "base_url": cloud["base_url"],
                "needs_key": True,
                "key_env": cloud["key_env"],
                "configured": bool(key),
                "detected": False,
                "models": [],
            }
        )
    return out


async def detect_locals(client: httpx.AsyncClient) -> list[dict[str, Any]]:
    results = []
    for spec in LOCALS:
        results.append(await _probe_local(client, spec))
    return results


async def list_models(
    client: httpx.AsyncClient, provider: str, detected: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Live model list when reachable/keyed, curated fallback otherwise."""
    if provider in detected and detected[provider].get("detected"):
        entry = detected[provider]
        return {"models": entry.get("models", []), "source": "live"}
    for cloud in CLOUDS:
        if cloud["id"] == provider:
            key = get_key(provider)
            if not key:
                if provider == "anthropic":
                    return {
                        "models": [
                            "claude-opus-4-6",
                            "claude-sonnet-4-6",
                            "claude-haiku-4-5",
                        ],
                        "source": "curated",
                    }
                return {"models": [], "source": "curated"}
            try:
                if provider == "openai":
                    resp = await client.get(
                        cloud["models_url"],
                        headers={"Authorization": f"Bearer {key}"},
                        timeout=PROBE_TIMEOUT_S,
                    )
                    if resp.status_code == 200:
                        ids = [m.get("id", "") for m in resp.json().get("data", [])]
                        return {"models": sorted(i for i in ids if i), "source": "live"}
                elif provider == "anthropic":
                    return {
                        "models": [
                            "claude-opus-4-6",
                            "claude-sonnet-4-6",
                            "claude-haiku-4-5",
                        ],
                        "source": "curated",
                    }
            except httpx.HTTPError as exc:
                logger.warning("Model list for %s failed: %s", provider, exc)
            return {"models": [], "source": "curated"}
    return {"models": [], "source": "curated"}


async def chat_once(
    client: httpx.AsyncClient,
    provider: str,
    model: str,
    messages: list[dict[str, str]],
    detected: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Non-streaming completion via the backend proxy (keys never leave)."""
    chunks: list[str] = []
    async for text in chat_stream(client, provider, model, messages, detected):
        chunks.append(text)
    return {"success": True, "message": "Chat complete", "data": {"reply": "".join(chunks)}}


async def chat_stream(  # noqa: C901 - provider dispatch is inherently branchy
    client: httpx.AsyncClient,
    provider: str,
    model: str,
    messages: list[dict[str, str]],
    detected: dict[str, dict[str, Any]],
):
    """Yield reply text deltas. Local + OpenAI stream; Anthropic aggregates."""
    if provider in detected and detected[provider].get("detected"):
        base = detected[provider]["base_url"]
        url = f"{base}/v1/chat/completions" if provider != "ollama" else f"{base}/api/chat"
        if provider == "ollama":
            payload = {
                "model": model,
                "messages": messages,
                "stream": True,
            }
            async with client.stream("POST", url, json=payload, timeout=CHAT_TIMEOUT_S) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except ValueError:
                        continue
                    text = obj.get("message", {}).get("content", "")
                    if text:
                        yield text
            return
        payload = {"model": model, "messages": messages, "stream": True}
        async with client.stream("POST", url, json=payload, timeout=CHAT_TIMEOUT_S) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except ValueError:
                    continue
                for choice in obj.get("choices", []):
                    text = choice.get("delta", {}).get("content", "")
                    if text:
                        yield text
        return
    key = get_key(provider)
    if not key:
        raise ValueError(f"No API key configured for {provider}")
    if provider == "openai":
        payload = {"model": model, "messages": messages, "stream": True}
        async with client.stream(
            "POST",
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}"},
            json=payload,
            timeout=CHAT_TIMEOUT_S,
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except ValueError:
                    continue
                for choice in obj.get("choices", []):
                    text = choice.get("delta", {}).get("content", "")
                    if text:
                        yield text
        return
    if provider == "anthropic":
        system = ""
        turns = []
        for msg in messages:
            if msg.get("role") == "system":
                system += msg.get("content", "")
            else:
                turns.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
        payload: dict[str, Any] = {"model": model, "max_tokens": 1024, "messages": turns}
        if system:
            payload["system"] = system
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": _ANTHROPIC_VERSION,
                "content-type": "application/json",
            },
            json=payload,
            timeout=CHAT_TIMEOUT_S,
        )
        resp.raise_for_status()
        for block in resp.json().get("content", []):
            if block.get("type") == "text":
                yield block.get("text", "")
        return
    raise ValueError(f"Unknown provider: {provider}")


def get_gpus() -> list[dict[str, Any]]:
    """Enumerate NVIDIA GPUs via nvidia-smi. Empty = single/non-NVIDIA."""
    try:
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.info("nvidia-smi unavailable: %s", exc)
        return []
    gpus = []
    for line in proc.stdout.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) != 3:
            continue
        try:
            gpus.append({"index": int(parts[0]), "name": parts[1], "vramMb": int(float(parts[2]))})
        except ValueError:
            continue
    return gpus


def onboarding_payload(
    detected_locals: list[dict[str, Any]], gpus: list[dict[str, Any]]
) -> dict[str, Any]:
    usable = [d for d in detected_locals if d.get("detected")]
    clouds_keyed = [c["id"] for c in CLOUDS if get_key(c["id"])]
    if usable or clouds_keyed:
        path = "ready"
    elif gpus:
        path = "install_local"
    else:
        path = "cloud_key"
    return {
        "ready": bool(usable or clouds_keyed),
        "recommended_path": path,
        "facts": [
            "Local providers are free and private (Ollama, LM Studio, vLLM).",
            "Cloud providers need an API key, pasted once in Settings.",
            "On dual-GPU machines the webapp model targets the secondary card.",
        ],
        "locals": [d["id"] for d in usable],
        "clouds_keyed": clouds_keyed,
        "gpus": gpus,
    }


_INSTALL_JOBS: dict[str, dict[str, Any]] = {}
_INSTALL_LOCK = threading.Lock()


def _run_winget_ollama(job_id: str) -> None:
    with _INSTALL_LOCK:
        _INSTALL_JOBS[job_id]["status"] = "running"
    try:
        proc = subprocess.run(
            ["winget", "install", "--id", "Ollama.Ollama", "-e", "--silent"],
            capture_output=True,
            text=True,
            timeout=600,
        )
        ok = proc.returncode == 0
        detail = (proc.stdout + proc.stderr)[-2000:]
    except (OSError, subprocess.SubprocessError) as exc:
        ok, detail = False, str(exc)
    with _INSTALL_LOCK:
        _INSTALL_JOBS[job_id].update(
            {"status": "done" if ok else "failed", "detail": detail, "ended": time.time()}
        )


def start_install(engine: str) -> dict[str, Any]:
    """One-click engine install. Fixed allowlist only: {'ollama'}."""
    if engine != "ollama":
        return {"success": False, "message": f"Install not supported for: {engine}"}
    job_id = f"install-{uuid.uuid4().hex[:8]}"
    with _INSTALL_LOCK:
        _INSTALL_JOBS[job_id] = {"status": "queued", "engine": engine, "started": time.time()}
    thread = threading.Thread(target=_run_winget_ollama, args=(job_id,), daemon=True)
    thread.start()
    return {"success": True, "message": "Ollama install started", "data": {"job_id": job_id}}


def install_status(job_id: str) -> dict[str, Any]:
    with _INSTALL_LOCK:
        job = dict(_INSTALL_JOBS.get(job_id, {}))
    if not job:
        return {"success": False, "message": f"Unknown job: {job_id}", "data": {}}
    return {"success": True, "message": f"Job {job['status']}", "data": job}
