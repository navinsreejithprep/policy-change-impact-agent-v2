from app.graph import nodes as N
from app.graph.workflow import start_analysis

CYBER_REGULATION = "Material cyber incidents must be reported to the regulator within 24 hours."


def test_evidence_decision_loops_when_thin():
    state = {"evidence_gaps": ["missing owner"], "evidence_iterations": 0, "max_evidence_iterations": 2}
    assert N.evidence_decision(state) == "more"


def test_evidence_decision_stops_at_limit():
    state = {"evidence_gaps": ["missing owner"], "evidence_iterations": 2, "max_evidence_iterations": 2}
    assert N.evidence_decision(state) == "insufficient"


def test_evidence_decision_proceeds_when_sufficient():
    state = {"evidence_gaps": [], "evidence_iterations": 0, "max_evidence_iterations": 2}
    assert N.evidence_decision(state) == "impact"


def test_retrieve_evidence_flags_missing_categories():
    state = {
        "knowledge_results": [
            {"id": "x", "type": "Process", "title": "Some Process", "path": "processes/x.md", "content": "..."}
        ]
    }
    N.retrieve_evidence(state)
    gaps_text = " ".join(state["evidence_gaps"]).lower()
    assert "owner" in gaps_text
    assert "control" in gaps_text
    assert not any(g.startswith("No documented internal process") for g in state["evidence_gaps"])


def test_full_graph_thin_evidence_loops_then_reports_insufficient(monkeypatch):
    monkeypatch.setattr(N, "search_knowledge", lambda q, limit=8: [])
    monkeypatch.setattr(N, "expand_links", lambda hits, limit=20: hits)

    r = start_analysis(CYBER_REGULATION)

    assert r["report"]["status"] == "insufficient_evidence"
    assert r["report"]["missing"]
    # two retries (more_evidence) plus the initial pass = 3 "checking evidence" mentions
    assert sum("evidence" in s.lower() for s in r["status"]) >= 3
