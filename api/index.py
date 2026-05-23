# api/index.py
import sys
from pathlib import Path

# Make sure fastapi_app is importable
sys.path.insert(0, str(Path(__file__).parent.parent / "fastapi_app"))

from main import app  # noqa: E402 — Vercel picks this up as the ASGI handler
