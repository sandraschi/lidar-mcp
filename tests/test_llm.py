"""llm_providers + companions unit tests — no network, no hardware."""

import json

import pytest

from lidar_mcp import companions, llm_providers


@pytest.fixture()
def _keystore(tmp_path, monkeypatch):
    path = tmp_path / "llm_keys.json"
    monkeypatch.setattr(llm_providers, "_keystore_path", lambda: path)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return path


def test_key_roundtrip(_keystore):
    assert llm_providers.get_key("openai") == ""
    assert llm_providers.set_key("openai", "sk-test")["success"] is True
    assert llm_providers.get_key("openai") == "sk-test"
    assert llm_providers.delete_key("openai")["success"] is True
    assert llm_providers.get_key("openai") == ""


def test_env_wins_over_keystore(_keystore, monkeypatch):
    llm_providers.set_key("openai", "sk-file")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
    assert llm_providers.get_key("openai") == "sk-env"


def test_set_key_unknown_provider(_keystore):
    assert llm_providers.set_key("nope", "x")["success"] is False


def test_keystore_chmod_0600(_keystore):
    import os
    import stat
    import sys

    llm_providers.set_key("anthropic", "sk-ant")
    assert _keystore.is_file()
    if sys.platform != "win32":
        mode = stat.S_IMODE(os.stat(_keystore).st_mode)
        assert mode == 0o600


def test_providers_shape_hides_keys(_keystore):
    llm_providers.set_key("openai", "sk-secret-value")
    merged = llm_providers.list_providers_sync_shape([])
    assert "sk-secret-value" not in json.dumps(merged)
    openai = next(p for p in merged if p["id"] == "openai")
    assert openai["configured"] is True
    assert openai["needs_key"] is True


async def test_models_curated_fallback(_keystore):
    import httpx

    async with httpx.AsyncClient() as client:
        result = await llm_providers.list_models(client, "anthropic", {})
    assert result["source"] == "curated"
    assert result["models"]


async def test_models_unknown_provider(_keystore):
    import httpx

    async with httpx.AsyncClient() as client:
        result = await llm_providers.list_models(client, "nope", {})
    assert result == {"models": [], "source": "curated"}


def test_onboarding_paths(_keystore):
    ready = llm_providers.onboarding_payload([{"id": "ollama", "detected": True}], [])
    assert ready["ready"] is True and ready["recommended_path"] == "ready"
    install = llm_providers.onboarding_payload([], [{"index": 0}])
    assert install["recommended_path"] == "install_local"
    cloud = llm_providers.onboarding_payload([], [])
    assert cloud["recommended_path"] == "cloud_key"


def test_gpus_failsoft():
    gpus = llm_providers.get_gpus()
    assert isinstance(gpus, list)


def test_install_allowlist():
    assert llm_providers.start_install("nope")["success"] is False
    assert llm_providers.install_status("job-missing")["success"] is False


async def test_chat_unknown_provider_raises(_keystore):
    import httpx

    async with httpx.AsyncClient() as client:
        with pytest.raises(ValueError):
            await llm_providers.chat_once(client, "nope", "m", [], {})


async def test_companion_unknown():
    import httpx

    async with httpx.AsyncClient() as client:
        result = await companions.probe_companion(client, "nope")
    assert result["success"] is False


def test_companion_registry_lists_planned_nori():
    ids = {c["id"]: c for c in companions.list_companions()}
    assert ids["yahboom"]["status"] == "live"
    assert ids["norirobotics"]["status"] == "planned"
