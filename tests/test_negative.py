from __future__ import annotations
import pytest
from core import config
from core.client import DeepseekClient
from tests.stub_server import StubServer

def _ok_body(content: str = "ok") -> dict:
    return {"choices": [{"message": {"content": content}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}


def _client(server: StubServer) -> DeepseekClient:
    return DeepseekClient(api_key="test-key", base_url=server.base_url, timeout=5)


@pytest.fixture
def require_real():
    if config.USE_FAKE:
        pytest.skip("离线模式不使用真实接口")


def test_401_is_returned():
    with StubServer() as server:
        server.enqueue(401, {"error": {"message": "invalid api key"}})
        with _client(server) as client:
            result = client.ask("hi")
    assert result.status_code == 401 and "invalid api key" in result.error_message
    assert server.calls == 1


def test_429_is_retried():
    with StubServer() as server:
        server.enqueue(429, {"error": {"message": "rate limited"}})
        server.enqueue(200, _ok_body())
        with _client(server) as client:
            result = client.ask("hi")
    assert result.status_code == 200 and server.calls == 2


def test_500_is_retried():
    with StubServer() as server:
        server.enqueue(500, {"error": {"message": "boom"}})
        server.enqueue(500, {"error": {"message": "boom"}})
        server.enqueue(200, _ok_body())
        with _client(server) as client:
            result = client.ask("hi")
    assert result.status_code == 200 and server.calls == 3


def test_malformed_json_is_reported():
    with StubServer() as server:
        server.enqueue(200, "not json")
        with _client(server) as client:
            result = client.ask("hi")
    assert result.status_code == 200 and result.content == ""
    assert "not json" in result.error_message


@pytest.mark.live
def test_invalid_api_key_live(require_real):
    with DeepseekClient(api_key="sk-invalid-key-for-test") as client:
        result = client.ask("hi")
    assert result.status_code in (401, 403) and result.error_message


@pytest.mark.live
def test_unknown_model_live(api_client, require_real):
    result = api_client.ask("hi", model="deepseek-not-exist")
    assert result.status_code in (400, 404), result.error_message


@pytest.mark.live
def test_response_contract(api_client, require_real):
    result = api_client.ask("你好")
    assert result.status_code == 200, result.error_message
    body = result.body
    for key in ("id", "object", "created", "model", "choices", "usage"):
        assert key in body, f"缺少字段 {key}"
    choice = body["choices"][0]
    assert choice["message"]["role"] == "assistant"
    assert choice["finish_reason"] in {"stop", "length", "content_filter", "tool_calls"}
    usage = body["usage"]
    assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]
