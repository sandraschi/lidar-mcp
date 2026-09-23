"""lidar-mcp web backend (FastAPI).

Serves the SOTA webapp: LiDAR REST (scan/map/diff/status), LLM provider
proxy (local discovery + cloud keys, keys never leave the server), robot
companion probes (fail-soft), logs ring buffer, and the built SPA itself
(``webapp/dist`` when present). Single process on LIDAR_API_PORT (11217).

MCP serving is unchanged: stdio (Claude Desktop) and SSE (11075) via
``lidar_mcp.main``. This backend is REST-only — no ``mcp.http_app()``
mount, so BUG-008/BUG-038 do not apply.
"""

from __future__ import annotations

import asyncio
import collections
import inspect
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from lidar_mcp import companions, llm_providers
from lidar_mcp.tools import lidar_tools

logger = logging.getLogger(__name__)

API_PORT = int(os.environ.get("LIDAR_API_PORT", "11217"))
DEV_FRONTEND = int(os.environ.get("LIDAR_WEB_PORT", "11218"))

_STARTED = time.monotonic()


def _version() -> str:
    try:
        from importlib.metadata import version

        return version("lidar-mcp")
    except Exception:
        return "0.0.0"


# --- log ring buffer -------------------------------------------------------

LOGS: collections.deque[dict[str, Any]] = collections.deque(maxlen=500)


class _RingHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            LOGS.append(
                {
                    "ts": time.strftime("%H:%M:%S", time.localtime(record.created)),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }
            )
        except Exception:
            pass


logging.getLogger().addHandler(_RingHandler())

# --- app -------------------------------------------------------------------

app = FastAPI(title="lidar-mcp web backend", version=_version())

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://127.0.0.1:{DEV_FRONTEND}",
        f"http://localhost:{DEV_FRONTEND}",
        f"http://127.0.0.1:{API_PORT}",
        f"http://localhost:{API_PORT}",
    ],
    # Unconditional LAN + Tailscale regex (fleet CORS standard): the Pi-served
    # UI must work from laptop/phone browsers, not just localhost.
    allow_origin_regex=(
        r"http://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+"
        r"|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+"
        r"|100\.\d+\.\d+\.\d+)(:\d+)?"
    ),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_http: httpx.AsyncClient | None = None
_detected: dict[str, dict[str, Any]] = {}


async def _client() -> httpx.AsyncClient:
    global _http
    if _http is None:
        _http = httpx.AsyncClient()
    return _http


async def _refresh_detection() -> list[dict[str, Any]]:
    """Probe local engines; refresh the shared detected map (parallel)."""
    global _detected
    client = await _client()
    found = await llm_providers.detect_locals(client)
    _detected = {d["id"]: d for d in found}
    return found


# --- core ------------------------------------------------------------------


@app.get("/api/health")
async def api_health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": _version(),
        "uptime_s": round(time.monotonic() - _STARTED, 1),
    }


@app.get("/api/status")
async def api_status() -> dict[str, Any]:
    scans = await lidar_tools.lidar_scan(operation="scans")
    saved = scans.get("data", {}).get("scans", []) if scans.get("success") else []
    return {
        "status": "ok",
        "version": _version(),
        "uptime_s": round(time.monotonic() - _STARTED, 1),
        "tool_count": 3,
        "saved_scans": len(saved),
        "lidar_configured": bool(os.environ.get("LIDAR_PORT", "")),
        "ports": {"sse": 11075, "api": API_PORT, "web": DEV_FRONTEND},
    }


@app.get("/api/dashboard")
async def api_dashboard() -> dict[str, Any]:
    status = await api_status()
    return {
        "success": True,
        "message": "Dashboard stats",
        "data": {
            "kpis": [
                {"name": "Tools", "value": status["tool_count"], "hint": "MCP tools"},
                {"name": "Saved scans", "value": status["saved_scans"], "hint": "in data/scans"},
                {
                    "name": "LiDAR",
                    "value": "ready" if status["lidar_configured"] else "no port",
                    "hint": "LIDAR_PORT",
                },
                {"name": "Uptime", "value": f"{status['uptime_s']:.0f}s", "hint": "web backend"},
            ]
        },
    }


def _tool_info(fn: Any) -> dict[str, Any]:
    doc = inspect.getdoc(fn) or ""
    params = []
    try:
        for name, param in inspect.signature(fn).parameters.items():
            if name in ("ctx",):
                continue
            default = None if param.default is inspect.Parameter.empty else str(param.default)
            params.append({"name": name, "default": default})
    except (TypeError, ValueError):
        params = []
    return {
        "name": fn.__name__,
        "summary": doc.splitlines()[0] if doc else "",
        "docstring": doc,
        "parameters": params,
        "portmanteau": fn.__name__ == "lidar_scan",
    }


@app.get("/api/tools")
async def api_tools() -> dict[str, Any]:
    tools = [
        _tool_info(lidar_tools.lidar_scan),
        _tool_info(lidar_tools.show_lidar_health_card),
        _tool_info(lidar_tools.lidar_shutdown),
    ]
    return {"success": True, "message": f"{len(tools)} tools", "data": {"tools": tools}}


@app.get("/api/skills")
async def api_skills() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[2]
    skills = []
    for path in sorted(root.glob(".opencode/skills/*/SKILL.md")):
        try:
            skills.append(
                {"name": path.parent.name, "source": "opencode", "markdown": path.read_text()}
            )
        except OSError:
            continue
    return {"success": True, "message": f"{len(skills)} skills", "data": {"skills": skills}}


@app.get("/api/logs")
async def api_logs() -> dict[str, Any]:
    return {"success": True, "message": f"{len(LOGS)} entries", "data": {"logs": list(LOGS)}}


# --- lidar -----------------------------------------------------------------


@app.get("/api/ports")
async def api_ports() -> dict[str, Any]:
    return await lidar_tools.lidar_scan(operation="ports")


class ScanBody(BaseModel):
    port: str = ""
    timeout_s: float = 3.0


@app.post("/api/scan")
async def api_scan(body: ScanBody) -> dict[str, Any]:
    try:
        return await lidar_tools.lidar_scan(
            operation="scan", port=body.port, timeout_s=body.timeout_s
        )
    except Exception as exc:
        logger.exception("POST /api/scan failed")
        return {"success": False, "message": f"scan failed: {exc}", "data": {}}


@app.get("/api/scans")
async def api_scans() -> dict[str, Any]:
    return await lidar_tools.lidar_scan(operation="scans")


class MapBody(BaseModel):
    source: str = "live"
    format: str = "both"
    grid_size: int = 100
    range_max_mm: float = 0.0
    timeout_s: float = 3.0


@app.post("/api/map")
async def api_map(body: MapBody) -> dict[str, Any]:
    try:
        return await lidar_tools.lidar_scan(
            operation="map",
            source=body.source,
            format=body.format,
            grid_size=body.grid_size,
            range_max_mm=body.range_max_mm,
            timeout_s=body.timeout_s,
        )
    except Exception as exc:
        logger.exception("POST /api/map failed")
        return {"success": False, "message": f"map failed: {exc}", "data": {}}


class DiffBody(BaseModel):
    scan_a: str = ""
    scan_b: str = ""
    sector_deg: float = 5.0
    tolerance_mm: float = 150.0


@app.post("/api/diff")
async def api_diff(body: DiffBody) -> dict[str, Any]:
    try:
        return await lidar_tools.lidar_scan(
            operation="diff",
            scan_a=body.scan_a,
            scan_b=body.scan_b,
            sector_deg=body.sector_deg,
            tolerance_mm=body.tolerance_mm,
        )
    except Exception as exc:
        logger.exception("POST /api/diff failed")
        return {"success": False, "message": f"diff failed: {exc}", "data": {}}


class SaveBody(BaseModel):
    port: str = ""
    timeout_s: float = 3.0
    note: str = ""


@app.post("/api/scans/save")
async def api_save(body: SaveBody) -> dict[str, Any]:
    try:
        return await lidar_tools.lidar_scan(
            operation="save", port=body.port, timeout_s=body.timeout_s, note=body.note
        )
    except Exception as exc:
        logger.exception("POST /api/scans/save failed")
        return {"success": False, "message": f"save failed: {exc}", "data": {}}


# --- llm proxy (keys never leave the server) --------------------------------


@app.get("/api/llm/discover")
async def llm_discover() -> dict[str, Any]:
    found = await _refresh_detection()
    return {"success": True, "message": "Local engines probed", "data": {"providers": found}}


@app.get("/api/llm/providers")
async def api_llm_providers() -> dict[str, Any]:
    found = await _refresh_detection()
    merged = llm_providers.list_providers_sync_shape(found)
    return {"success": True, "message": f"{len(merged)} providers", "data": {"providers": merged}}


@app.get("/api/llm/models")
async def llm_models(provider: str = "") -> dict[str, Any]:
    await _refresh_detection()
    result = await llm_providers.list_models(await _client(), provider, _detected)
    return {"success": True, "message": f"Models for {provider}", "data": result}


@app.get("/api/llm/gpus")
async def llm_gpus() -> dict[str, Any]:
    gpus = await asyncio.to_thread(llm_providers.get_gpus)
    return {"success": True, "message": f"{len(gpus)} GPUs", "data": {"gpus": gpus}}


@app.get("/api/llm/onboarding")
async def llm_onboarding() -> dict[str, Any]:
    found = await _refresh_detection()
    gpus = await asyncio.to_thread(llm_providers.get_gpus)
    payload = llm_providers.onboarding_payload(found, gpus)
    return {"success": True, "message": "Starter facts", "data": payload}


class ChatBody(BaseModel):
    provider: str = ""
    model: str = ""
    messages: list[dict[str, str]] = []


@app.post("/api/llm/chat")
async def llm_chat(body: ChatBody) -> dict[str, Any]:
    try:
        return await llm_providers.chat_once(
            await _client(), body.provider, body.model, body.messages, _detected
        )
    except Exception as exc:
        logger.exception("POST /api/llm/chat failed")
        return {"success": False, "message": f"chat failed: {exc}", "data": {}}


@app.post("/api/llm/chat/stream")
async def llm_chat_stream(body: ChatBody) -> StreamingResponse:
    client = await _client()
    detected = dict(_detected)

    async def gen():
        try:
            async for text in llm_providers.chat_stream(
                client, body.provider, body.model, body.messages, detected
            ):
                yield f"data: {json.dumps({'delta': text})}\n\n"
        except Exception as exc:
            logger.exception("Chat stream failed")
            yield f"data: {json.dumps({'error': str(exc)[:300]})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


class KeyBody(BaseModel):
    provider: str = ""
    api_key: str = ""


@app.post("/api/settings/llm")
async def llm_set_key(body: KeyBody) -> dict[str, Any]:
    if not body.api_key:
        return {"success": False, "message": "Empty key — not stored"}
    result = await asyncio.to_thread(llm_providers.set_key, body.provider, body.api_key)
    data = {
        "keys_configured": {
            c["id"]: bool(llm_providers.get_key(c["id"])) for c in llm_providers.CLOUDS
        }
    }
    if result.get("success"):
        return {"success": True, "message": result["message"], "data": data}
    return {"success": False, "message": result.get("message", "store failed"), "data": data}


@app.delete("/api/settings/llm/key")
async def llm_delete_key(provider: str = "") -> dict[str, Any]:
    result = await asyncio.to_thread(llm_providers.delete_key, provider)
    return result


@app.get("/api/settings/llm")
async def llm_settings() -> dict[str, Any]:
    flags = {c["id"]: bool(llm_providers.get_key(c["id"])) for c in llm_providers.CLOUDS}
    return {"success": True, "message": "Key flags only", "data": {"keys_configured": flags}}


class InstallBody(BaseModel):
    engine: str = "ollama"


@app.post("/api/llm/install")
async def llm_install(body: InstallBody) -> dict[str, Any]:
    return await asyncio.to_thread(llm_providers.start_install, body.engine)


@app.get("/api/llm/install/status")
async def llm_install_status(job_id: str = "") -> dict[str, Any]:
    return llm_providers.install_status(job_id)


# --- companions (fail-soft, one hop) ----------------------------------------


@app.get("/api/companions")
async def api_companions() -> dict[str, Any]:
    return {
        "success": True,
        "message": f"{len(companions.COMPANIONS)} companions",
        "data": {"companions": companions.list_companions()},
    }


@app.get("/api/companions/{companion_id}")
async def api_companion(companion_id: str) -> dict[str, Any]:
    return await companions.probe_companion(await _client(), companion_id)


# --- shutdown (fleet launcher contract) -------------------------------------


@app.post("/api/shutdown")
async def api_shutdown() -> dict[str, Any]:
    async def _exit_later() -> None:
        await asyncio.sleep(0.5)
        os._exit(0)

    asyncio.create_task(_exit_later())
    logger.warning("Shutdown requested via POST /api/shutdown")
    return {"success": True, "message": "Shutdown scheduled"}


# --- SPA (built frontend, when present) --------------------------------------


def _dist_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "webapp" / "dist"


@app.get("/{path:path}")
async def spa_fallback(request: Request, path: str) -> Any:
    dist = _dist_dir()
    if not dist.is_dir():
        return JSONResponse({"detail": "webapp not built — run bun run build in webapp/"}, 404)
    candidate = dist / path
    if path and candidate.is_file():
        return FileResponse(candidate)
    index = dist / "index.html"
    if index.is_file():
        return FileResponse(index)
    return JSONResponse({"detail": "webapp dist incomplete"}, 404)


def serve() -> None:
    import uvicorn

    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    uvicorn.run(app, host="127.0.0.1", port=API_PORT, log_level="info")


if __name__ == "__main__":
    serve()
