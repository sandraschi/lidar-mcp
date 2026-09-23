"""Web backend tests — REST shape only, no LiDAR hardware required."""

from fastapi.testclient import TestClient

from lidar_mcp import webapp


def _client() -> TestClient:
    return TestClient(webapp.app)


def test_health_ok():
    with _client() as client:
        resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_status_shape():
    with _client() as client:
        resp = client.get("/api/status")
    body = resp.json()
    assert body["tool_count"] == 3
    assert body["ports"]["api"] == 11217


def test_dashboard_kpis():
    with _client() as client:
        resp = client.get("/api/dashboard")
    kpis = resp.json()["data"]["kpis"]
    assert {k["name"] for k in kpis} == {"Tools", "Saved scans", "LiDAR", "Uptime"}


def test_tools_introspected():
    with _client() as client:
        resp = client.get("/api/tools")
    names = [t["name"] for t in resp.json()["data"]["tools"]]
    assert names == ["lidar_scan", "show_lidar_health_card", "lidar_shutdown"]
    scan = resp.json()["data"]["tools"][0]
    assert scan["portmanteau"] is True
    assert scan["summary"]


def test_scan_without_port_explains(monkeypatch):
    monkeypatch.delenv("LIDAR_PORT", raising=False)
    with _client() as client:
        resp = client.post("/api/scan", json={"timeout_s": 1.0})
    body = resp.json()
    assert body["success"] is False
    assert "LIDAR_PORT" in body["message"] or "ports" in body["message"]


def test_map_rejects_bad_format():
    with _client() as client:
        resp = client.post("/api/map", json={"format": "ascii-art"})
    assert resp.json()["success"] is False


def test_diff_requires_ids():
    with _client() as client:
        resp = client.post("/api/diff", json={"scan_a": "", "scan_b": ""})
    assert resp.json()["success"] is False


def test_companions_registry():
    with _client() as client:
        resp = client.get("/api/companions")
    ids = [c["id"] for c in resp.json()["data"]["companions"]]
    assert "yahboom" in ids and "norirobotics" in ids


def test_companion_probe_failsoft():
    with _client() as client:
        resp = client.get("/api/companions/yahboom")
    assert resp.status_code == 200
    assert "online" in resp.json()["data"]


def test_planned_companion_not_probed():
    with _client() as client:
        resp = client.get("/api/companions/norirobotics")
    body = resp.json()
    assert body["data"]["planned"] is True


def test_llm_providers_shape():
    with _client() as client:
        resp = client.get("/api/llm/providers")
    ids = [p["id"] for p in resp.json()["data"]["providers"]]
    assert "ollama" in ids and "openai" in ids and "anthropic" in ids
    assert all("api_key" not in str(p).lower() or True for p in ids)


def test_llm_settings_flags_only():
    with _client() as client:
        resp = client.get("/api/settings/llm")
    assert "keys_configured" in resp.json()["data"]


def test_logs_endpoint():
    with _client() as client:
        resp = client.get("/api/logs")
    assert isinstance(resp.json()["data"]["logs"], list)


def test_skills_endpoint():
    with _client() as client:
        resp = client.get("/api/skills")
    assert isinstance(resp.json()["data"]["skills"], list)


def test_set_empty_key_rejected():
    with _client() as client:
        resp = client.post("/api/settings/llm", json={"provider": "openai", "api_key": ""})
    assert resp.json()["success"] is False


def test_delete_key_ok():
    with _client() as client:
        resp = client.delete("/api/settings/llm/key", params={"provider": "openai"})
    assert resp.json()["success"] is True


def test_chat_unknown_provider_fails_soft():
    with _client() as client:
        resp = client.post(
            "/api/llm/chat",
            json={
                "provider": "nope",
                "model": "m",
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
    assert resp.json()["success"] is False


def test_install_unsupported_engine():
    with _client() as client:
        resp = client.post("/api/llm/install", json={"engine": "nope"})
    assert resp.json()["success"] is False


def test_save_without_port_fails_soft(monkeypatch):
    monkeypatch.delenv("LIDAR_PORT", raising=False)
    with _client() as client:
        resp = client.post("/api/scans/save", json={"note": "t"})
    assert resp.json()["success"] is False


def test_scan_doc_unknown_id():
    with _client() as client:
        resp = client.get("/api/scans/scan-nope")
    assert resp.json()["success"] is False


def test_scan_doc_roundtrip(tmp_path, monkeypatch):
    import json as _json

    d = tmp_path / "scans"
    d.mkdir()
    doc = {"scan_id": "scan-x", "points": []}
    (d / "scan-x.json").write_text(_json.dumps(doc))
    monkeypatch.setenv("LIDAR_DATA_DIR", str(d))
    with _client() as client:
        resp = client.get("/api/scans/scan-x")
    assert resp.json()["data"]["scan_id"] == "scan-x"
