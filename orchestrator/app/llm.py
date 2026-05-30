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
    error: str = ""


async def status() -> dict[str, object]:
    if not settings.ollama_enabled:
        return {"enabled": False, "provider": "ollama", "status": "disabled", "role_models": settings.role_models()}

    payload: dict[str, object] = {
        "enabled": True,
        "provider": "ollama",
        "base_url": settings.ollama_base_url,
        "default_model": settings.default_model,
        "role_models": settings.role_models(),
    }
    url = f"{settings.ollama_base_url.rstrip('/')}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout_seconds) as client:
            response = await client.get(url)
            response.raise_for_status()
        return {**payload, "status": "ok"}
    except Exception as exc:
        return {**payload, "status": "unreachable", "error": str(exc)}


def generate_sync(prompt: str, model: str) -> LLMResult:
    if not settings.ollama_enabled:
        return LLMResult(
            ok=False,
            response="",
            model=model,
            provider="ollama",
            duration_ms=0,
            error="OLLAMA_ENABLED=false; LLM calls are disabled.",
        )

    url = f"{settings.ollama_base_url.rstrip('/')}/api/generate"
    payload = {"model": model, "prompt": prompt, "stream": False}
    started = monotonic()
    try:
        with httpx.Client(timeout=settings.ollama_timeout_seconds) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            duration_ms = int((monotonic() - started) * 1000)
            return LLMResult(
                ok=True,
                response=str(data.get("response", "")),
                model=model,
                provider="ollama",
                duration_ms=duration_ms,
            )
    except Exception as exc:
        duration_ms = int((monotonic() - started) * 1000)
        return LLMResult(
            ok=False,
            response="",
            model=model,
            provider="ollama",
            duration_ms=duration_ms,
            error=f"External Ollama-compatible endpoint call failed: {exc}",
        )


async def generate(prompt: str, model: str | None = None) -> dict[str, str | bool | int]:
    selected_model = model or settings.default_model
    if not settings.ollama_enabled:
        return {"ok": False, "error": "OLLAMA_ENABLED=false; LLM calls are disabled.", "model": selected_model}

    url = f"{settings.ollama_base_url.rstrip('/')}/api/generate"
    payload = {"model": selected_model, "prompt": prompt, "stream": False}
    started = monotonic()
    try:
        async with httpx.AsyncClient(timeout=settings.ollama_timeout_seconds) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return {
                "ok": True,
                "response": data.get("response", ""),
                "model": selected_model,
                "duration_ms": int((monotonic() - started) * 1000),
            }
    except Exception as exc:
        return {
            "ok": False,
            "error": f"External Ollama-compatible endpoint call failed: {exc}",
            "model": selected_model,
            "duration_ms": int((monotonic() - started) * 1000),
        }
