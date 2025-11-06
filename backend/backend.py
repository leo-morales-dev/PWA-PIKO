"""Expose the FastAPI app when Render runs commands from ``backend/``.

Render executes both the build and start commands from the directory defined
in ``rootDir``.  When ``rootDir`` is ``backend`` the import path changes, so we
provide this tiny shim that re-exports ``main.app``.  This keeps
``uvicorn backend:app`` functional regardless of the working directory.
"""

from main import app  # noqa: F401

__all__ = ["app"]
