"""Regression tests for tenant data and session isolation."""

from __future__ import annotations

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

import api_server


@pytest.fixture(autouse=True)
def setup_api_server_dirs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # 1. Mock home to tmp_path so it doesn't affect user files
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    
    # 2. Reset the tenant caches before each test
    monkeypatch.setattr(api_server, "_session_services", {})
    
    # 3. Configure admin key
    monkeypatch.setenv("API_AUTH_KEY", "admin_secret")
    monkeypatch.setattr(api_server, "_API_KEY", "admin_secret")
    
    # 4. Mock the AGENT_DIR and local config folders to use tmp_path
    monkeypatch.setattr(api_server, "AGENT_DIR", tmp_path)
    # Mock the directory resolution helpers so default tenant uses tmp_path,
    # but other tenants still resolve dynamically to their isolated directories.
    from src.config.paths import active_tenant_var, get_runtime_root
    monkeypatch.setattr(api_server, "_get_sessions_dir", lambda: (
        tmp_path / "sessions" if active_tenant_var.get() == "default"
        else get_runtime_root() / "sessions"
    ))
    monkeypatch.setattr(api_server, "_get_runs_dir", lambda: (
        tmp_path / "runs" if active_tenant_var.get() == "default"
        else get_runtime_root() / "runs"
    ))
    monkeypatch.setattr(api_server, "_get_uploads_dir", lambda: (
        tmp_path / "uploads" if active_tenant_var.get() == "default"
        else get_runtime_root() / "uploads"
    ))


def _local_client() -> TestClient:
    """Return a TestClient that simulates a loopback caller."""
    return TestClient(api_server.app, client=("127.0.0.1", 50000))


def test_tenant_session_and_goal_isolation() -> None:
    client = _local_client()
    admin_headers = {"Authorization": "Bearer admin_secret"}

    # 1. Create two tenants
    resp = client.post("/admin/tenants/keys", headers=admin_headers, json={"name": "Tenant A"})
    assert resp.status_code == 200
    tenant_a_key = resp.json()["key"]
    tenant_a_id = resp.json()["tenant_id"]

    resp = client.post("/admin/tenants/keys", headers=admin_headers, json={"name": "Tenant B"})
    assert resp.status_code == 200
    tenant_b_key = resp.json()["key"]
    tenant_b_id = resp.json()["tenant_id"]

    headers_a = {"Authorization": f"Bearer {tenant_a_key}"}
    headers_b = {"Authorization": f"Bearer {tenant_b_key}"}

    # 2. Tenant A creates a session
    resp = client.post("/sessions", headers=headers_a, json={"title": "Session for Tenant A", "config": {}})
    assert resp.status_code == 201
    session_id = resp.json()["session_id"]

    # 3. Verify Tenant A can list and retrieve it
    resp = client.get("/sessions", headers=headers_a)
    assert resp.status_code == 200
    sessions = resp.json()
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == session_id

    resp = client.get(f"/sessions/{session_id}", headers=headers_a)
    assert resp.status_code == 200

    # 4. Verify Tenant B cannot list nor retrieve it (404)
    resp = client.get("/sessions", headers=headers_b)
    assert resp.status_code == 200
    assert len(resp.json()) == 0

    resp = client.get(f"/sessions/{session_id}", headers=headers_b)
    assert resp.status_code == 404

    # 5. Tenant A creates a goal for the session
    resp = client.post(
        f"/sessions/{session_id}/goal",
        headers=headers_a,
        json={
            "objective": "Tenant A objective",
            "criteria": ["Thesis 1"],
            "risk_tier": "research_general",
        }
    )
    assert resp.status_code == 201

    # 6. Verify Tenant A can get the goal, but Tenant B gets 404
    resp = client.get(f"/sessions/{session_id}/goal", headers=headers_a)
    assert resp.status_code == 200
    assert resp.json()["goal"]["objective"] == "Tenant A objective"

    resp = client.get(f"/sessions/{session_id}/goal", headers=headers_b)
    assert resp.status_code == 404


def test_tenant_upload_isolation() -> None:
    client = _local_client()
    admin_headers = {"Authorization": "Bearer admin_secret"}

    # Create two tenants
    resp = client.post("/admin/tenants/keys", headers=admin_headers, json={"name": "Tenant A"})
    tenant_a_key = resp.json()["key"]
    tenant_a_id = resp.json()["tenant_id"]

    resp = client.post("/admin/tenants/keys", headers=admin_headers, json={"name": "Tenant B"})
    tenant_b_key = resp.json()["key"]
    tenant_b_id = resp.json()["tenant_id"]

    headers_a = {"Authorization": f"Bearer {tenant_a_key}"}
    headers_b = {"Authorization": f"Bearer {tenant_b_key}"}

    # Verify that the upload folders for both tenants are different
    # (they will be created dynamically when we request uploads)
    
    # We will upload a file as Tenant A
    file_payload = {"file": ("test.txt", b"secret tenant content", "text/plain")}
    resp = client.post("/upload", headers=headers_a, files=file_payload)
    assert resp.status_code == 200
    safe_name = resp.json()["file_path"].split("/")[-1]

    # Check the host directory structures
    # Tenant A's upload should be under <tmp_path>/.vibe-trading-cnx/tenants/<tenant_a_id>/uploads/
    tenant_a_uploads_dir = Path.home() / ".vibe-trading-cnx" / "tenants" / tenant_a_id / "uploads"
    assert (tenant_a_uploads_dir / safe_name).exists()
    
    # Tenant B's upload folder should not even have Tenant A's file
    tenant_b_uploads_dir = Path.home() / ".vibe-trading-cnx" / "tenants" / tenant_b_id / "uploads"
    assert not (tenant_b_uploads_dir / safe_name).exists()


def test_admin_elevation_keeps_tenant_context(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _local_client()
    admin_headers = {"Authorization": "Bearer admin_secret"}

    # 1. Create a tenant
    resp = client.post("/admin/tenants/keys", headers=admin_headers, json={"name": "Tenant A"})
    assert resp.status_code == 200
    tenant_a_key = resp.json()["key"]
    tenant_a_id = resp.json()["tenant_id"]

    headers_a = {"Authorization": f"Bearer {tenant_a_key}"}

    # 2. Tenant A creates a session
    resp = client.post("/sessions", headers=headers_a, json={"title": "Session A", "config": {}})
    assert resp.status_code == 201
    session_id = resp.json()["session_id"]

    # 3. Inject a mock admin session token
    monkeypatch.setattr(api_server, "_ADMIN_SESSION_TOKENS", {"mock-admin-token"})

    # 4. Request with BOTH tenant bearer token and elevated admin token
    headers_elevated = {
        "Authorization": f"Bearer {tenant_a_key}",
        "x-admin-token": "mock-admin-token",
    }
    resp = client.get("/sessions", headers=headers_elevated)
    assert resp.status_code == 200
    sessions = resp.json()
    # It must return Tenant A's sessions (length 1), NOT default tenant's sessions (length 0)!
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == session_id
