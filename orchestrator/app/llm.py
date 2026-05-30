import httpx

from .config import settings


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
