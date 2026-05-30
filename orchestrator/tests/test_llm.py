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
        def raise_for_status(self):
            return None

    class Client:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url):
            return Response()

    monkeypatch.setattr(llm.settings, "ollama_enabled", True)
    monkeypatch.setattr(llm.settings, "ollama_base_url", "http://ollama.example.local:11434")
    monkeypatch.setattr(llm.httpx, "AsyncClient", Client)

    status = await llm.status()

    assert status["status"] == "ok"
    assert status["role_models"]["analyst"] == llm.settings.model_for_role("analyst")
