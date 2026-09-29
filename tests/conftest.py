"""Test-wide fixtures.

Tests run against the deterministic fallback path of the LLM layer by
default so the suite is fast, free, and reproducible. Live-LLM behaviour is
exercised manually / via the running app, not the automated test suite —
matching the "saved snapshots for evaluation, live search for demos" split
in the spec.
"""
import pytest

import app.llm as llm_module


@pytest.fixture(autouse=True)
def no_live_llm(monkeypatch):
    monkeypatch.setattr(llm_module, "OPENAI_API_KEY", None)
