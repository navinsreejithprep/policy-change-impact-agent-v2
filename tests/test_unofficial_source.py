from app.graph import nodes as N
from app.graph.workflow import start_analysis

DISCOVERY_QUERY = "Find the latest official cybersecurity incident reporting requirement and assess its impact."


def test_unofficial_only_results_retry_until_limit_then_insufficient(monkeypatch):
    calls = []

    def fake_search(query, limit=6, exclude_domains=None):
        calls.append(exclude_domains)
        return [
            {
                "url": "https://lawfirm-blog.example.com/commentary",
                "title": "Commentary on the new rule",
                "content": "Some commentary.",
                "authority": "secondary",
            }
        ]

    monkeypatch.setattr(N, "fc_search", fake_search)

    r = start_analysis(DISCOVERY_QUERY)

    assert len(calls) == 3  # default max_source_search_attempts
    assert r["awaiting_confirmation"] is False
    assert r["report"]["status"] == "insufficient_evidence"


def test_unofficial_first_then_official_succeeds(monkeypatch):
    calls = {"n": 0}

    def fake_search(query, limit=6, exclude_domains=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return [
                {
                    "url": "https://news.example.com/story",
                    "title": "News story",
                    "content": "A blog wrote about the change.",
                    "authority": "secondary",
                }
            ]
        return [
            {
                "url": "https://www.sebi.gov.in/circular",
                "title": "SEBI Circular",
                "content": "This is notified and gazetted. Material incidents must be reported within 24 hours.",
                "authority": "official",
            }
        ]

    monkeypatch.setattr(N, "fc_search", fake_search)

    r = start_analysis(DISCOVERY_QUERY)

    assert calls["n"] == 2
    assert r["awaiting_confirmation"] is True
    assert r["confirmation"]["authority"] == "official"
