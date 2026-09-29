from app.graph import nodes as N
from app.graph.workflow import resume_analysis, start_analysis

CYBER_REGULATION = "Material cyber incidents must be reported to the regulator within 24 hours."
DISCOVERY_QUERY = "Find the latest official cybersecurity incident reporting requirement and assess its impact."


def test_supplied_regulation_skips_firecrawl(monkeypatch):
    calls = []
    monkeypatch.setattr(N, "fc_search", lambda *a, **k: calls.append(1) or [])

    r = start_analysis(CYBER_REGULATION)

    assert calls == []
    assert any("skipped web search" in s.lower() for s in r["status"])
    assert r["awaiting_confirmation"] is False
    assert r["report"]["status"] in ("complete", "insufficient_evidence")


def test_official_source_requires_confirmation_then_completes(monkeypatch):
    def fake_search(query, limit=6, exclude_domains=None):
        return [
            {
                "url": "https://www.cert-in.org.in/notice",
                "title": "CERT-In Notice",
                "content": (
                    "Material cyber incidents must be reported to the regulator within 24 hours. "
                    "This notification is gazetted and comes into force immediately."
                ),
                "authority": "official",
            }
        ]

    monkeypatch.setattr(N, "fc_search", fake_search)

    r = start_analysis(DISCOVERY_QUERY)
    assert r["awaiting_confirmation"] is True
    assert r["confirmation"]["authority"] == "official"
    assert r["confirmation"]["version_status"] == "final"
    assert r["confirmation"]["content_hash"].startswith("sha256:")

    r2 = resume_analysis(r["thread_id"], "confirm")
    assert r2["awaiting_confirmation"] is False
    assert r2["report"]["status"] == "complete"
    assert r2["report"]["sources"][0]["authority"] == "official"


def test_human_can_reject_source_and_search_again(monkeypatch):
    calls = {"n": 0}

    def fake_search(query, limit=6, exclude_domains=None):
        calls["n"] += 1
        domain = "www.cert-in.org.in" if calls["n"] == 1 else "www.rbi.org.in"
        return [
            {
                "url": f"https://{domain}/notice-{calls['n']}",
                "title": "Notice",
                "content": "Material cyber incidents must be reported within 24 hours. Gazetted.",
                "authority": "official",
            }
        ]

    monkeypatch.setattr(N, "fc_search", fake_search)

    r = start_analysis(DISCOVERY_QUERY)
    assert r["awaiting_confirmation"] is True
    first_url = r["confirmation"]["url"]

    r2 = resume_analysis(r["thread_id"], "search_again")
    assert calls["n"] == 2
    assert r2["awaiting_confirmation"] is True
    assert r2["confirmation"]["url"] != first_url


def test_empty_input_is_invalid():
    r = start_analysis("   ")
    assert r["awaiting_confirmation"] is False
    assert r["report"]["status"] == "invalid_input"


def test_force_supplied_skips_search_regardless_of_phrasing(monkeypatch):
    """force_supplied=True (used for uploaded regulation documents) must
    bypass the free-text phrasing/length heuristic entirely — a real
    document's extracted text won't always contain "must"/"shall"/etc, and
    uploading it is already an unambiguous signal that it's the regulation."""
    calls = []
    monkeypatch.setattr(N, "fc_search", lambda *a, **k: calls.append(1) or [])

    ambiguous_text = "Cyber incidents get reported to the regulator inside a day."
    r = start_analysis(ambiguous_text, force_supplied=True)

    assert calls == []
    assert any("skipped web search" in s.lower() for s in r["status"])
    assert r["report"]["status"] != "insufficient_evidence"
