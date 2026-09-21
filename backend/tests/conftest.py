"""
conftest.py — ensures PYTHONPATH is set correctly for all backend tests.
This allows imports like `from backend.app.xxx` and `from ai.xxx` to resolve
regardless of which directory pytest is invoked from.
"""
import sys
import os

# Add the project root to sys.path so both `backend` and `ai` packages resolve
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
