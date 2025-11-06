"""Expose the FastAPI application for ASGI servers."""

from .main import app  # noqa: F401  (re-export for ASGI servers)

__all__ = ["app"]
