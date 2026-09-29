"""Runs the whole discovery -> confirmation -> analysis flow purely from a
previously saved source snapshot, with Firecrawl mocked out entirely. This is
the offline evaluation path: CI/tests must never depend on live web results,
even though the same code path also supports live discovery for demos.
"""
import json
from pathlib import Path

from app.graph import nodes as N
from app.graph.workflow import resume_analysis, start_analysis

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures" / "saved_cert_in_notice.json").read_text()
)


def test_saved_snapshot_flows_end_to_end_without_network(monkeypatch):
    def fake_search(query, limit=6, exclude_domains=None):
        return [
            {
                "url": FIXTURE["url"],
                "title": FIXTURE["title"],
                "content": FIXTURE["content"],
                "authority": FIXTURE["authority"],
            }
        ]

    monkeypatch.setattr(N, "fc_search", fake_search)

    r = start_analysis("Find the latest official cybersecurity incident reporting requirement.")
    assert r["awaiting_confirmation"] is True
    assert r["confirmation"]["url"] == FIXTURE["url"]
    assert r["confirmation"]["version_status"] == "final"

    r2 = resume_analysis(r["thread_id"], "confirm")
    assert r2["report"]["status"] == "complete"
    assert r2["report"]["sources"][0]["url"] == FIXTURE["url"]
    assert r2["report"]["regulatory_requirements"]
