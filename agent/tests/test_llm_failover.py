import os
from unittest.mock import MagicMock, patch
import pytest
import openai
from langchain_core.outputs import ChatResult, ChatGeneration
from langchain_core.messages import AIMessage

from src.providers.llm import build_llm
from src.providers.key_pool import LLMKeyPoolManager
from src.config.paths import active_tenant_var


@pytest.fixture(autouse=True)
def clean_pool():
    manager = LLMKeyPoolManager()
    manager.clear()
    yield
    manager.clear()


def test_llm_failover_retry():
    """Verify that ChatOpenAIWithReasoning transparently fails over to next key on 429 RateLimitError."""
    tenant_id = "tenant_failover"
    active_tenant_var.set(tenant_id)
    
    # We configure a pool of two keys
    tenant_env = {
        "LANGCHAIN_PROVIDER": "openai",
        "LANGCHAIN_MODEL_NAME": "gpt-4o",
        "OPENAI_API_KEY": "failed-key,working-key",
        "OPENAI_BASE_URL": "https://api.openai.com/v1"
    }
    
    with patch("src.config.paths.get_tenant_env_values", return_value=tenant_env):
        llm = build_llm(model_name="gpt-4o")
        
        # Verify first key in pool is used initially
        assert llm.openai_api_key.get_secret_value() == "failed-key"
        
        # We mock the _generate call on the superclass (ChatOpenAI)
        # First call (with failed-key): raise RateLimitError
        # Second call (with working-key): return a valid ChatResult
        mock_response = ChatResult(generations=[ChatGeneration(message=AIMessage(content="Hello!"))])
        
        call_count = 0
        
        def mock_super_generate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Mock a RateLimitError
                mock_request = MagicMock()
                mock_request.headers = {}
                raise openai.RateLimitError(
                    message="Rate limit exceeded",
                    response=MagicMock(status_code=429, headers={}),
                    body={}
                )
            return mock_response
            
        with patch("langchain_openai.chat_models.base.ChatOpenAI._generate", side_effect=mock_super_generate):
            # Invoke the LLM
            result = llm.generate(messages=[[]])
            
            # The result should be successful, and the key should have rotated to "working-key"
            assert result.generations[0][0].text == "Hello!"
            assert call_count == 2
            assert llm.openai_api_key.get_secret_value() == "working-key"
            
            # The failed-key should be cooling
            pool_key = (tenant_id, "openai")
            pool = LLMKeyPoolManager()._pools[pool_key]
            assert pool[0].key == "failed-key"
            assert pool[0].status == "cooling"
            assert pool[1].key == "working-key"
            assert pool[1].status == "active"
