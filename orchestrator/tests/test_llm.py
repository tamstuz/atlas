import pytest

from orchestrator.app import llm


@pytest.fixture
def anyio_backend():
    return "asyncio"


def test_model_for_role_falls_back_to_default(monkeypatch):
    monkeypatch.setattr(llm.settings, "default_model", "default-test-model")
    monkeypatch.setattr(llm.settings, "analyst_model", None)
    monkeypatch.setattr(llm.settings, "qa_model", "qa-test-model")

    assert llm.settings.model_for_role("analyst") == "default-test-model"
    assert llm.settings.model_for_role("qa") == "qa-test-model"


@pytest.mark.anyio
async def test_llm_status_reachable(monkeypatch):
    class Response:
        def __init__(self, data=None):
            self._data = data or {}

        def raise_for_status(self):
            return None

        def json(self):
            return self._data

    class Client:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url):
            return Response()

        async def post(self, url, json):
            self.generate_payload = json
            return Response({"response": "OK", "done": True})

    monkeypatch.setattr(llm.settings, "ollama_enabled", True)
    monkeypatch.setattr(llm.settings, "ollama_base_url", "http://ollama.example.local:11434")
    monkeypatch.setattr(llm.httpx, "AsyncClient", Client)

    status = await llm.status()

    assert status["status"] == "ok"
    assert status["model_status"] == "ok"
    assert status["role_models"]["analyst"] == llm.settings.model_for_role("analyst")


def test_generate_sync_records_endpoint_and_timeout_when_unreachable(monkeypatch):
    monkeypatch.setattr(llm.settings, "ollama_enabled", True)
    monkeypatch.setattr(llm.settings, "ollama_base_url", "http://127.0.0.1:9")
    monkeypatch.setattr(llm.settings, "llm_timeout_seconds", 120.0)
    monkeypatch.setattr(llm.settings, "ollama_timeout_seconds", None)

    result = llm.generate_sync("Say OK only.", "gemma4:26b")

    assert result.ok is False
    assert result.endpoint == "http://127.0.0.1:9/api/generate"
    assert result.timeout_seconds == 120.0
    assert "http://127.0.0.1:9/api/generate" in result.error
    assert "120.0s" in result.error
