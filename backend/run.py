"""
backend/run.py
─────────────────────────────────────────────────────────────
Local development server launcher.

Appends the project root to ``sys.path`` so that absolute imports
(``backend.app.…``) resolve correctly, then starts Uvicorn in
hot-reload mode on ``0.0.0.0:8000``.
"""

from __future__ import annotations

import os
import sys

import uvicorn

# Append parent directory to sys.path to enable 'backend.app...' absolute imports
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
