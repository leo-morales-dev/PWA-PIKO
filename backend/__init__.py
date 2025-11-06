"""Backend package entrypoint.

Expose the FastAPI ``app`` defined in ``backend.main`` so deployment
platforms that import ``backend:app`` (like Render) can locate the
application object without duplicating the initialization code.
"""

from .main import app

__all__ = ["app"]
