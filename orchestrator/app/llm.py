import httpx

from .config import settings


async def status() -> dict[str, object]:
    if not settings.ollama_enabled:
        return {"enabled": False, "provider": "ollama", "status": "disabled"}

    payload: dict[str, object] = {
        "enabled": True,
        "provider": "ollama",
        "base_url": settings.ollama_base_url,
        "default_model": settings.default_model,
    }
    url = f"{settings.ollama_base_url.rstrip('/')}/api/tags"
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(url)
            response.raise_for_status()
        return {**payload, "status": "ok"}
    except Exception as exc:
        return {**payload, "status": "unreachable", "error": str(exc)}


async def generate(prompt: str) -> dict[str, str | bool]:
    if not settings.ollama_enabled:
        return {"ok": False, "error": "OLLAMA_ENABLED=false; LLM calls are disabled."}

    url = f"{settings.ollama_base_url.rstrip('/')}/api/generate"
    payload = {"model": settings.default_model, "prompt": prompt, "stream": False}
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return {"ok": True, "response": data.get("response", "")}
    except Exception as exc:
        return {"ok": False, "error": f"External Ollama-compatible endpoint call failed: {exc}"}
