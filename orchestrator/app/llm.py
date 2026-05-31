from dataclasses import dataclass
from time import monotonic

import httpx

from .config import settings


@dataclass
class LLMResult:
    ok: bool
    response: str
    model: str
    provider: str
    duration_ms: int
    endpoint: str
    timeout_seconds: float
    error: str = ""


def _generate_endpoint() -> str:
    return f"{settings.ollama_base_url.rstrip('/')}/api/generate"


def _tags_endpoint() -> str:
    return f"{settings.ollama_base_url.rstrip('/')}/api/tags"


def _timeout() -> float:
    return settings.effective_llm_timeout_seconds


async def status() -> dict[str, object]:
    if not settings.ollama_enabled:
        return {"enabled": False, "provider": "ollama", "status": "disabled", "role_models": settings.role_models()}

    payload: dict[str, object] = {
        "enabled": True,
        "provider": "ollama",
        "base_url": settings.ollama_base_url,
        "default_model": settings.default_model,
        "role_models": settings.role_models(),
        "timeout_seconds": _timeout(),
    }
    try:
        async with httpx.AsyncClient(timeout=_timeout()) as client:
            tags_response = await client.get(_tags_endpoint())
            tags_response.raise_for_status()
            generate_response = await client.post(
                _generate_endpoint(),
                json={"model": settings.default_model, "prompt": "Say OK only.", "stream": False},
            )
            generate_response.raise_for_status()
            data = generate_response.json()
        if not data.get("done", False):
            return {**payload, "status": "unreachable", "error": "model validation did not complete"}
        return {**payload, "status": "ok", "model_status": "ok"}
    except Exception as exc:
        return {
            **payload,
            "status": "unreachable",
            "error": f"{_generate_endpoint()} timed out after {_timeout()}s or failed: {exc}",
        }


def generate_sync(prompt: str, model: str) -> LLMResult:
    endpoint = _generate_endpoint()
    timeout_seconds = _timeout()
    if not settings.ollama_enabled:
        return LLMResult(
            ok=False,
            response="",
            model=model,
            provider="ollama",
            duration_ms=0,
            endpoint=endpoint,
            timeout_seconds=timeout_seconds,
            error="OLLAMA_ENABLED=false; LLM calls are disabled.",
        )

    payload = {"model": model, "prompt": prompt, "stream": False}
    started = monotonic()
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.post(endpoint, json=payload)
            response.raise_for_status()
            data = response.json()
            duration_ms = int((monotonic() - started) * 1000)
            return LLMResult(
                ok=True,
                response=str(data.get("response", "")),
                model=model,
                provider="ollama",
                duration_ms=duration_ms,
                endpoint=endpoint,
                timeout_seconds=timeout_seconds,
            )
    except Exception as exc:
        duration_ms = int((monotonic() - started) * 1000)
        return LLMResult(
            ok=False,
            response="",
            model=model,
            provider="ollama",
            duration_ms=duration_ms,
            endpoint=endpoint,
            timeout_seconds=timeout_seconds,
            error=f"External Ollama-compatible endpoint call failed at {endpoint} after {timeout_seconds}s: {exc}",
        )


async def generate(prompt: str, model: str | None = None) -> dict[str, str | bool | int | float]:
    selected_model = model or settings.default_model
    result = generate_sync(prompt, selected_model)
    return {
        "ok": result.ok,
        "response": result.response,
        "error": result.error,
        "model": result.model,
        "provider": result.provider,
        "duration_ms": result.duration_ms,
        "endpoint": result.endpoint,
        "timeout_seconds": result.timeout_seconds,
    }
