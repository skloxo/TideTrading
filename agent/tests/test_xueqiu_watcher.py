import pytest
import json
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.platforms.xueqiu_watcher import XueqiuWatcher
import api_server


@pytest.mark.anyio
async def test_xueqiu_watcher_shared_pool_and_rotation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # 1. Setup paths
    monkeypatch.setattr("src.config.paths.get_data_dir", lambda *args, **kwargs: tmp_path)
    
    # Mock tenant keys to return tenant_1 and tenant_2
    mock_tenants = [
        {"tenant_id": "tenant_1", "key": "key_1", "name": "Tenant 1", "is_active": True},
        {"tenant_id": "tenant_2", "key": "key_2", "name": "Tenant 2", "is_active": True},
    ]
    monkeypatch.setattr(api_server, "_load_tenant_keys", lambda: mock_tenants)
    
    # 2. Write configs for default, tenant_1, tenant_2
    # tenant_1 config: monitors ZH123456
    t1_dir = tmp_path / "tenants" / "tenant_1"
    t1_dir.mkdir(parents=True, exist_ok=True)
    t1_config = {
        "enabled": True,
        "feishu_webhook": "https://webhook.feishu/t1",
        "combos": {"ComboA": "ZH123456"},
        "watch_uids": {},
        "xq_tokens": ["token_t1"]
    }
    (t1_dir / "xueqiu_monitor.json").write_text(json.dumps(t1_config), encoding="utf-8")
    
    # tenant_2 config: also monitors ZH123456
    t2_dir = tmp_path / "tenants" / "tenant_2"
    t2_dir.mkdir(parents=True, exist_ok=True)
    t2_config = {
        "enabled": True,
        "feishu_webhook": "https://webhook.feishu/t2",
        "combos": {"ComboB": "ZH123456"},
        "watch_uids": {},
        "xq_tokens": ["token_t2"]
    }
    (t2_dir / "xueqiu_monitor.json").write_text(json.dumps(t2_config), encoding="utf-8")
    
    # Mock get_data_dir dynamically based on active context
    from src.config.paths import active_tenant_var
    def mock_get_data_dir():
        tenant = active_tenant_var.get()
        if tenant == "default":
            return tmp_path
        return tmp_path / "tenants" / tenant
        
    monkeypatch.setattr("src.config.paths.get_data_dir", mock_get_data_dir)
    
    watcher = XueqiuWatcher(check_interval_seconds=300)
    
    # Mock network request to return sample
    mock_rebal = [
        {
            "updated_at": 1698234720000,
            "stock_symbol": "SH600519",
            "stock_name": "贵州茅台",
            "operation": "买入",
            "price": "1800",
            "current_weight": 10.0,
            "prev_weight": 0.0,
            "position_change": 10.0,
            "trade_time": "2026-07-07 09:30:00"
        }
    ]
    
    # Patch _query_combo and _query_influencer_watchlist
    query_combo_mock = MagicMock(return_value=mock_rebal)
    monkeypatch.setattr(watcher, "_query_combo", query_combo_mock)
    
    # Mock Feishu notification
    from unittest.mock import AsyncMock
    notify_mock = AsyncMock()
    monkeypatch.setattr(watcher, "_notify_feishu", notify_mock)
    
    # 3. First tick
    await watcher.tick()
    
    # Assert _query_combo was called exactly ONCE (because of de-duplication/Shared Cache Pool)
    assert query_combo_mock.call_count == 1
    
    # Assert token used was token_t1 or token_t2
    first_call_args = query_combo_mock.call_args[0]
    assert first_call_args[0] == "ZH123456"
    assert first_call_args[1][0] in ["token_t1", "token_t2"]
    first_token_used = first_call_args[1][0]
    
    # Check that logs were written to both tenant directories
    assert (t1_dir / "xueqiu_rebalancing_logs.json").exists()
    assert (t2_dir / "xueqiu_rebalancing_logs.json").exists()
    
    # 4. Second tick - check cookie rotation
    query_combo_mock.reset_mock()
    await watcher.tick()
    assert query_combo_mock.call_count == 1
    second_call_args = query_combo_mock.call_args[0]
    
    # It should have rotated to the other token
    second_token_used = second_call_args[1][0]
    assert second_token_used in ["token_t1", "token_t2"]
    assert second_token_used != first_token_used
