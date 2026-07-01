import os
import threading
import time
from unittest.mock import patch
import pytest

from src.config.paths import active_tenant_var
from src.providers.llm import build_llm


def test_llm_build_no_environ_pollution():
    """Verify that build_llm resolves credentials without modifying the underlying raw os.environ."""
    # Ensure OPENAI_API_KEY is not set globally in the real OS environment
    os.environ.pop("OPENAI_API_KEY", None)
    os.environ.pop("OPENAI_API_BASE", None)
    if "OPENAI_API_KEY" in os.environ._data:
        del os.environ._data["OPENAI_API_KEY"]
    if "OPENAI_API_BASE" in os.environ._data:
        del os.environ._data["OPENAI_API_BASE"]
    
    tenant_env = {
        "LANGCHAIN_PROVIDER": "openai",
        "LANGCHAIN_MODEL_NAME": "gpt-4o",
        "OPENAI_API_KEY": "sk-tenant-secret-key",
        "OPENAI_BASE_URL": "https://api.tenant.com/v1"
    }
    
    active_tenant_var.set("tenant_123")
    
    with patch("src.config.paths.get_tenant_env_values", return_value=tenant_env):
        llm = build_llm(model_name="gpt-4o")
        
        # The instantiated LLM should have the correct key and base URL
        assert llm.openai_api_key.get_secret_value() == "sk-tenant-secret-key"
        assert llm.openai_api_base == "https://api.tenant.com/v1"
        
        # The real global OS environment must NOT contain the tenant key!
        assert "OPENAI_API_KEY" not in os.environ._data
        assert "OPENAI_API_BASE" not in os.environ._data


def test_llm_concurrency_isolation():
    """Verify concurrency isolation: two threads constructing different LLMs concurrently do not leak keys."""
    results = {}

    def side_effect(tenant):
        if tenant == "tenant_A":
            return {
                "LANGCHAIN_PROVIDER": "openai",
                "LANGCHAIN_MODEL_NAME": "gpt-4-A",
                "OPENAI_API_KEY": "key-A",
                "OPENAI_BASE_URL": "https://base-A.com"
            }
        elif tenant == "tenant_B":
            return {
                "LANGCHAIN_PROVIDER": "openai",
                "LANGCHAIN_MODEL_NAME": "gpt-4-B",
                "OPENAI_API_KEY": "key-B",
                "OPENAI_BASE_URL": "https://base-B.com"
            }
        return {}

    def worker(tenant_name, model_name):
        active_tenant_var.set(tenant_name)
        # Sleep a random small time to increase probability of race condition if there's global state
        time.sleep(0.05)
        llm = build_llm(model_name=model_name)
        results[tenant_name] = {
            "key": llm.openai_api_key.get_secret_value(),
            "base_url": llm.openai_api_base
        }

    # Patch get_tenant_env_values globally but use a thread-safe side_effect
    with patch("src.config.paths.get_tenant_env_values", side_effect=side_effect):
        t1 = threading.Thread(target=worker, args=("tenant_A", "gpt-4-A"))
        t2 = threading.Thread(target=worker, args=("tenant_B", "gpt-4-B"))
        
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        
    assert results["tenant_A"]["key"] == "key-A"
    assert results["tenant_A"]["base_url"] == "https://base-A.com"
    assert results["tenant_B"]["key"] == "key-B"
    assert results["tenant_B"]["base_url"] == "https://base-B.com"
