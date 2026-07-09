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
    monkeypatch.setattr("src.config.paths._get_active_runtime_dir", lambda *args, **kwargs: tmp_path)
    
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
    
    # Wire up MultiTenantEventDispatcher as in production
    from src.platforms.event_dispatcher import MultiTenantEventDispatcher
    dispatcher = MultiTenantEventDispatcher(config_provider=watcher.config_provider, watcher=watcher)
    watcher.add_event_listener(dispatcher.handle_event)
    
    # Mock data to return from queries
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
    
    # Mock initialize_combo_history and initialize_influencer_watchlist to avoid actual network calls
    monkeypatch.setattr(watcher, "initialize_combo_history", MagicMock())
    monkeypatch.setattr(watcher, "initialize_influencer_watchlist", MagicMock())
    
    # Mock Feishu notification in dispatcher
    from unittest.mock import AsyncMock
    notify_mock = AsyncMock()
    monkeypatch.setattr(dispatcher, "_notify_feishu", notify_mock)
    
    # Mock asyncio.sleep only in event_dispatcher to speed up its alert loop
    monkeypatch.setattr("src.platforms.event_dispatcher.asyncio.sleep", AsyncMock())
    
    async def await_dispatcher_tasks():
        for _ in range(50):
            dispatcher_tasks = [
                t for t in asyncio.all_tasks()
                if t.get_coro().__name__ in ("_process_combo", "_process_influencer", "_initialize_combo_history", "_initialize_influencer_watchlist")
            ]
            if not dispatcher_tasks:
                break
            await asyncio.gather(*dispatcher_tasks, return_exceptions=True)
            await asyncio.sleep(0.01)

    # 3. First tick
    await watcher.tick()
    
    # Await all background tasks to ensure they finish executing before assertions
    await await_dispatcher_tasks()
    
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

    # Check that persistent shared cache was created and contains the data
    cache_file = tmp_path / "shared_xueqiu_cache.json"
    assert cache_file.exists()
    cache_data = json.loads(cache_file.read_text(encoding="utf-8"))
    assert "combos" in cache_data
    assert "ZH123456" in cache_data["combos"]
    
    # 4. Second tick - check that we hit the persistent cache without doing a new query
    # (Since cached timestamp is current, query_combo should NOT be called again!)
    query_combo_mock.reset_mock()
    await watcher.tick()
    await await_dispatcher_tasks()
    # Call count must be 0 because of cache hit!
    assert query_combo_mock.call_count == 0

    # 5. Third tick - manually expire cache and check cookie rotation
    cache_data = json.loads(cache_file.read_text(encoding="utf-8"))
    cache_data["combos"]["ZH123456"]["timestamp"] = 0
    cache_file.write_text(json.dumps(cache_data), encoding="utf-8")
    
    query_combo_mock.reset_mock()
    await watcher.tick()
    await await_dispatcher_tasks()
    # Call count must be 1 because cache expired
    assert query_combo_mock.call_count == 1
    third_call_args = query_combo_mock.call_args[0]
    third_token_used = third_call_args[1][0]
    
    # It must be rotated to the other token
    assert third_token_used in ["token_t1", "token_t2"]
    assert third_token_used != first_token_used
