"""ASGI application export for ``uvicorn backend:app``."""

from .main import app  # noqa: F401  (re-export for ASGI servers)

__all__ = ["app"]
