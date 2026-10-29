"""
conftest.py - pytest loads this first, automatically.

1. Lets tests import the app packages (agents, tools) from the repo root.
2. Gives every test a `gemini` fixture: the fake model, already plugged in.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))           # repo root, for the app files
sys.path.insert(0, str(ROOT / "tests"))  # tests folder, for fake_gemini

from agents import agent_loop  # noqa: E402
from fake_gemini import FakeGemini  # noqa: E402


@pytest.fixture
def gemini(monkeypatch):
    """Replace genai.Client() with the fake, so no real model is called."""
    fake = FakeGemini()
    monkeypatch.setattr(agent_loop.genai, "Client", lambda: fake)
    return fake
