import pytest
import re
from pathlib import Path
from fastapi.testclient import TestClient
from agent import api_server

def test_parse_readme_changelog_isolation(tmp_path: Path):
    # Setup mock README file
    mock_readme = tmp_path / "README_zh.md"
    mock_content = """# Title
Some description.

## 📰 最新动态

- **2026-07-07** 🚀 **v1.7.5 — 雪球监控多租户联合查询与 Cookie 轮询 & 持久化共享缓存池 (性能与反爬专项)**：
  - **持久化共享缓存池 (Persistent Shared Cache Pool)**：底层引入了磁盘缓存。
  - **系统升级与版本比对重构**：修复升级拦截故障。

- **2026-07-06** 🚀 **v1.7.4 — 项目设置独立页面**：
  - **项目设置独立化**：提取设置至独立单页。

---

## ✨ 核心功能
Some features.
"""
    mock_readme.write_text(mock_content, encoding="utf-8")

    # Run parser
    entries = api_server._parse_readme_changelog(mock_readme, max_entries=5)
    
    assert len(entries) == 2
    
    # First entry checks
    assert entries[0]["v"] == "v1.7.5"
    assert entries[0]["date"] == "2026-07-07"
    assert "雪球监控多租户联合查询" in entries[0]["title"]
    assert "持久化共享缓存池" in entries[0]["body"]
    assert "系统升级与版本比对重构" in entries[0]["body"]
    
    # Second entry checks
    assert entries[1]["v"] == "v1.7.4"
    assert entries[1]["date"] == "2026-07-06"
    assert "项目设置独立页面" in entries[1]["title"]
    assert "项目设置独立化" in entries[1]["body"]


def test_get_system_changelog_api():
    client = TestClient(api_server.app)
    
    # Test GET endpoint
    response = client.get("/api/system/changelog?lang=zh")
    assert response.status_code == 200
    
    json_data = response.json()
    assert "changelog" in json_data
    assert isinstance(json_data["changelog"], list)
    
    # Check that it extracted elements from the real README
    if len(json_data["changelog"]) > 0:
        first = json_data["changelog"][0]
        assert "v" in first
        assert "date" in first
        assert "title" in first
        assert "body" in first
        assert first["v"].startswith("v")
