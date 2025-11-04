"""Module shim so ``uvicorn backend:app`` works even when executed from the
``backend`` directory (Render's root dir setting).
"""

from main import app  # noqa: F401

__all__ = ["app"]
