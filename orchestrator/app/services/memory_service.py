from ..config import settings


def qdrant_endpoint() -> str:
    return settings.qdrant_url
