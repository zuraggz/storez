"""Vercel entrypoint.

Vercel's Python runtime imports this module and serves the ASGI application it
exports as `app`. Everything else lives in the `app/` package, which
`vercel.json` bundles alongside this file.
"""

import sys
from pathlib import Path

# The project root is not on sys.path inside the function bundle.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app

__all__ = ["app"]
