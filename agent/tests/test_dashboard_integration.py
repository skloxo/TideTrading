import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

import api_server
from src.swarm.simulation_graph import SimulationGraphManager
from src.swarm.report_logger import ReportLogger

@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.delenv("API_AUTH_KEY", raising=False)
    monkeypatch.setenv("LANGCHAIN_MODEL_NAME", "deepseek-chat")
    monkeypatch.setenv("LANGCHAIN_PROVIDER", "deepseek")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "mock-key")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    
    # Mock ChatLLM.chat to avoid making real API requests during test execution
    from src.providers.chat import ChatLLM, LLMResponse
    monkeypatch.setattr(
        ChatLLM, 
        "chat", 
        lambda self, messages, **kwargs: LLMResponse(content="Mocked Agent response")
    )
    return TestClient(api_server.app, client=("127.0.0.1", 50000))

def test_simulation_graph_manager(tmp_path: Path):
    manager = SimulationGraphManager("test_tenant")
    # Reset file state
    if manager.file_path.exists():
        manager.file_path.unlink()
    manager._ensure_file()
    assert manager.file_path.exists()
    
    # Add dynamic nodes and links
    manager.add_node("node1", "Node One", "题材板块", value="100M")
    manager.add_link("node1", "node2", weight=0.9)
    
    data = manager.load()
    assert len(data["nodes"]) > 0
    assert any(n["id"] == "node1" for n in data["nodes"])
    assert any(l["source"] == "node1" and l["target"] == "node2" for l in data["links"])
    
    # Clean up
    if manager.file_path.exists():
        manager.file_path.unlink()

def test_report_logger(tmp_path: Path):
    logger = ReportLogger("test_tenant")
    logger.clear_logs()
    
    # Log ReACT stages
    logger.log_thought("Thinking about market direction...")
    logger.log_tool_call("InsightForge", {"query": "A-share"})
    logger.log_observation("Index rises by 1.2%")
    logger.log_decision("Decision: Stay bullish")
    
    assert logger.log_file_path.exists()
    
    # Verify entries
    with open(logger.log_file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        assert len(lines) == 4
        entries = [json.loads(line.strip()) for line in lines]
        assert entries[0]["action"] == "thought"
        assert entries[1]["action"] == "tool_call"
        assert entries[2]["action"] == "observation"
        assert entries[3]["action"] == "decision"
        
    logger.clear_logs()
    assert not logger.log_file_path.exists()

def test_dashboard_api_endpoints(client: TestClient):
    # Test ECharts Graph GET endpoint
    response = client.get("/settings/dashboard/graph")
    assert response.status_code == 200
    body = response.json()
    assert "nodes" in body
    assert "links" in body

    # Test ReACT Logs list GET endpoint
    response = client.get("/settings/dashboard/react-logs?stream=false")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)

    # Test Agent Chat POST endpoint
    response = client.post(
        "/settings/dashboard/agent-chat",
        json={"agent_id": "yuzi", "message": "What do you think of Wanfeng?"}
    )
    assert response.status_code == 200
    body = response.json()
    assert "response" in body
    assert body["response"] == "Mocked Agent response"
