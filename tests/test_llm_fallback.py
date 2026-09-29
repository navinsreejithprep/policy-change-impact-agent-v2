"""Regression tests for a real bug: extract()/impact() used to treat a
*successful* LLM call that legitimately returned an empty list the same as
the LLM call having failed outright, silently swapping in fallback content
(and, in impact(), the misleading "No live LLM analysis was available" text)
even though the LLM had, in fact, just run. The fix distinguishes the two by
checking `result is fallback` (structured_call returns that exact object
only on genuine failure).
"""
import app.graph.nodes as N


def test_impact_trusts_a_successful_empty_response_instead_of_masking_it(monkeypatch):
    monkeypatch.setattr(
        N,
        "structured_call",
        lambda prompt, fallback: {"impacts": [{"process": "X", "finding": "fine as-is", "priority": "Low", "confidence": "High", "evidence_ids": []}], "assumptions": [], "actions": []},
    )

    state = {"requirements": [], "evidence": []}
    N.impact(state)

    assert state["assumptions"] == []
    assert "No live LLM analysis was available" not in state["assumptions"]
    assert state["actions"] == []
    assert state["impacts"][0]["finding"] == "fine as-is"


def test_impact_uses_fallback_only_when_llm_genuinely_did_not_run():
    # relies on the autouse no_live_llm fixture (conftest.py), which patches
    # app.llm.OPENAI_API_KEY to None so structured_call always falls back
    state = {
        "requirements": [{"requirement": "x"}],
        "evidence": [{"id": "p1", "type": "Process", "title": "Some Process"}],
    }
    N.impact(state)

    assert state["assumptions"] == ["No live LLM analysis was available; deterministic fallback used."]
    assert state["impacts"][0]["process"] == "Some Process"


def test_extract_trusts_a_successful_empty_requirements_list(monkeypatch):
    monkeypatch.setattr(N, "structured_call", lambda prompt, fallback: {"requirements": []})

    state = {"user_input": "some ambiguous text", "regulation_text": "some ambiguous text"}
    N.extract(state)

    assert state["requirements"] == []


def test_extract_uses_fallback_only_when_llm_genuinely_did_not_run():
    # relies on the autouse no_live_llm fixture (conftest.py)
    state = {"user_input": "Material cyber incidents must be reported within 24 hours.", "regulation_text": "Material cyber incidents must be reported within 24 hours."}
    N.extract(state)

    assert state["requirements"][0]["requirement"] == state["user_input"]
