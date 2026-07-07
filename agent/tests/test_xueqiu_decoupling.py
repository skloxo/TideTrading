# -*- coding: utf-8 -*-
import pytest
import json
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
from src.platforms.xueqiu_watcher import XueqiuWatcher, ITenantConfigProvider, ICredentialProvider
from src.platforms.event_dispatcher import MultiTenantEventDispatcher

class DummyConfigProvider(ITenantConfigProvider):
    def __init__(self, tenants_dir: Path) -> None:
        self.tenants_dir = tenants_dir

    def get_active_tenants(self) -> list:
        return ["tenant_a", "tenant_b"]

    def get_tenant_xueqiu_config(self, tenant_id: str) -> dict:
        t_dir = self.tenants_dir / tenant_id
        t_dir.mkdir(parents=True, exist_ok=True)
        
        combos = {"ComboX": "ZH999999"} if tenant_id == "tenant_a" else {"ComboY": "ZH999999"}
        watch_uids = {"InfluencerX": "111111"} if tenant_id == "tenant_a" else {"InfluencerY": "111111"}
        
        return {
            "combos": combos,
            "watch_uids": watch_uids,
            "xq_tokens": [f"token_{tenant_id}"],
            "feishu_webhook": f"https://webhook.feishu.com/{tenant_id}",
            "data_dir": t_dir
        }

class DummyCredentialProvider(ICredentialProvider):
    def get_cooperative_cookies(self, tenant_ids: list) -> list:
        return [f"token_{tid}" for tid in tenant_ids]

@pytest.mark.anyio
async def test_xueqiu_decoupling_flow(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # 1. Setup mock directories
    monkeypatch.setattr("src.config.paths.get_data_dir", lambda *args, **kwargs: tmp_path)
    monkeypatch.setattr("src.config.paths._get_active_runtime_dir", lambda *args, **kwargs: tmp_path)
    
    from src.config.paths import active_tenant_var
    
    # 2. Instantiate decoupled Watcher and Dispatcher
    config_prov = DummyConfigProvider(tmp_path / "tenants")
    cred_prov = DummyCredentialProvider()
    
    watcher = XueqiuWatcher(
        check_interval_seconds=300,
        config_provider=config_prov,
        credential_provider=cred_prov
    )
    
    dispatcher = MultiTenantEventDispatcher(config_provider=config_prov, watcher=watcher)
    watcher.add_event_listener(dispatcher.handle_event)
    
    # Mock data to return from queries
    mock_rebal = [
        {
            "updated_at": 1698234720000,
            "stock_symbol": "SH600519",
            "stock_name": "贵州茅台",
            "operation": "加仓",
            "price": "1800",
            "current_weight": 15.0,
            "prev_weight": 10.0,
            "position_change": 5.0,
            "trade_time": "2026-07-07 09:35:00"
        }
    ]
    
    mock_stocks = [
        {
            "symbol": "SH601318",
            "name": "中国平安"
        }
    ]
    
    # Mock network query methods on XueqiuWatcher
    monkeypatch.setattr(watcher, "_query_combo", MagicMock(return_value=mock_rebal))
    monkeypatch.setattr(watcher, "_query_influencer_watchlist", MagicMock(return_value=mock_stocks))
    
    # Mock initialize methods
    monkeypatch.setattr(watcher, "initialize_combo_history", MagicMock())
    monkeypatch.setattr(watcher, "initialize_influencer_watchlist", MagicMock())
    
    # Mock the notifier in event dispatcher
    notify_feishu_mock = AsyncMock()
    notify_influencer_mock = AsyncMock()
    monkeypatch.setattr(dispatcher, "_notify_feishu", notify_feishu_mock)
    monkeypatch.setattr(dispatcher, "_notify_influencer_change", notify_influencer_mock)
    
    # Mock asyncio.sleep only in event_dispatcher to speed up its alert loop
    monkeypatch.setattr("src.platforms.event_dispatcher.asyncio.sleep", AsyncMock())
    
    # 3. Trigger the tick loop
    await watcher.tick()
    
    # Await all background tasks to ensure they finish executing before assertions
    pending = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)
    
    # 4. Assertions
    # Ensure logs were written to respective folders for AOP-driven Tenant Decoupling
    t1_log_path = tmp_path / "tenants" / "tenant_a" / "xueqiu_rebalancing_logs.json"
    t2_log_path = tmp_path / "tenants" / "tenant_b" / "xueqiu_rebalancing_logs.json"
    
    assert t1_log_path.exists()
    assert t2_log_path.exists()
    
    t1_logs = json.loads(t1_log_path.read_text(encoding="utf-8"))
    t2_logs = json.loads(t2_log_path.read_text(encoding="utf-8"))
    
    assert len(t1_logs) > 0
    # tenant_a monitored ComboX which got logs
    assert any(log.get("combo_name") == "ComboX" for log in t1_logs)
    
    # Ensure notifications were called
    assert notify_feishu_mock.call_count == 2
    assert notify_influencer_mock.call_count == 0  # first run is initialization, no changes
