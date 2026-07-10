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


@pytest.mark.anyio
async def test_executor_tenant_context_propagation(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _local_client()
    admin_headers = {"Authorization": "Bearer admin_secret"}

    # 1. Create a tenant A
    resp = client.post("/admin/tenants/keys", headers=admin_headers, json={"name": "Tenant A"})
    assert resp.status_code == 200
    tenant_a_key = resp.json()["key"]
    tenant_a_id = resp.json()["tenant_id"]

    # 2. Set active_tenant_var to Tenant A
    from src.config.paths import active_tenant_var
    active_tenant_var.set(tenant_a_id)

    # Initialize session service for Tenant A
    svc = api_server._get_session_service()
    assert svc is not None

    # 3. Create a session for Tenant A
    session = svc.create_session(title="Session Context Prop", config={})
    session_id = session.session_id

    # 4. Intercept ChatLLM, build_registry and AgentLoop
    import anyio
    captured_tenants = []

    class DummyLLM:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr("src.providers.chat.ChatLLM", DummyLLM)

    class DummyAgent:
        def __init__(self, *args, **kwargs):
            pass

        def run(self, user_message, history, session_id):
            from src.config.paths import active_tenant_var
            captured_tenants.append(active_tenant_var.get())
            return {"status": "success", "content": "mocked response", "run_dir": None}

    monkeypatch.setattr("src.agent.loop.AgentLoop", DummyAgent)

    def mock_build_registry(*args, **kwargs):
        from src.config.paths import active_tenant_var
        captured_tenants.append(active_tenant_var.get())
        from src.agent.tools import ToolRegistry
        return ToolRegistry()
    monkeypatch.setattr("src.tools.build_registry", mock_build_registry)

    # 5. Send message directly via service (triggers background execution in task)
    result = await svc.send_message(session_id, "test prompt")
    attempt_id = result["attempt_id"]

    # 6. Wait for execution to finish in the event loop
    attempt_info = None
    for _ in range(50):
        attempt = svc.store.get_attempt(session_id, attempt_id)
        if attempt:
            attempt_info = {"status": attempt.status.value, "error": attempt.error}
            if attempt.status.value in ("completed", "failed"):
                break
        await anyio.sleep(0.1)

    # 7. Verify ContextVar was correctly propagated inside the executor thread tasks
    assert len(captured_tenants) == 2
    for t in captured_tenants:
        assert t == tenant_a_id


def test_tenant_search_index_isolation(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.config.paths import active_tenant_var
    from src.session.search import get_shared_index, _shared_indexes

    # Reset/clear the cached shared indexes dict in-place
    _shared_indexes.clear()

    active_tenant_var.set("tenant_a")
    idx_a = get_shared_index()
    assert "tenant_a" in _shared_indexes
    assert idx_a.db_path.parent.name == "tenant_a"

    active_tenant_var.set("tenant_b")
    idx_b = get_shared_index()
    assert "tenant_b" in _shared_indexes
    assert idx_b.db_path.parent.name == "tenant_b"

    assert idx_a is not idx_b
    assert idx_a.db_path != idx_b.db_path
