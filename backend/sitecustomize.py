"""Runtime path adjustments for Render deployments.

Render may execute the app from the ``backend`` directory as the process
working directory. In that situation ``backend`` is no longer importable as a
package (because Python only sees modules relative to the working directory),
which makes ``uvicorn backend.main:app`` fail with ``ModuleNotFoundError``.

By extending ``sys.path`` with the repository root we ensure the ``backend``
package remains importable regardless of the working directory used to start
Uvicorn. Python imports this module automatically on startup when present on
the import path (``sitecustomize`` hook).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Determine the repository root (parent directory of this file's folder).
BACKEND_DIR = Path(__file__).resolve().parent
REPO_ROOT = BACKEND_DIR.parent

# Ensure the repository root is available on sys.path so ``import backend``
# works even when the working directory is ``backend`` itself.
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
