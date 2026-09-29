import io

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_analyze_file_extracts_text_and_runs_analysis(monkeypatch):
    import app.graph.nodes as N

    # keep this test offline: no Firecrawl calls should happen since the
    # uploaded text itself contains obligation language ("must be reported"),
    # so it should be classified as a supplied regulation
    called = []
    monkeypatch.setattr(N, "fc_search", lambda *a, **k: called.append(1) or [])

    content = b"Material cyber incidents must be reported to the regulator within 24 hours."
    files = {"file": ("regulation.txt", io.BytesIO(content), "text/plain")}

    res = client.post("/api/analyze-file", files=files)

    assert res.status_code == 200
    data = res.json()
    assert called == []
    assert any("skipped web search" in s.lower() for s in data["status"])
    assert data["report"]["status"] in ("complete", "insufficient_evidence")


def test_analyze_file_skips_search_even_without_obligation_phrasing(monkeypatch):
    """Reproduces a real reported bug: a document whose extracted text
    doesn't contain any of the free-text classifier's obligation markers
    (no "must"/"shall"/"required to"...) and is short was wrongly routed to
    the web-search path instead of being analyzed directly, since uploading
    a document is already an unambiguous signal of intent."""
    import app.graph.nodes as N

    called = []
    monkeypatch.setattr(N, "fc_search", lambda *a, **k: called.append(1) or [])

    # deliberately short, and phrased without any STRONG_REGULATION_MARKERS
    content = b"Cyber incidents get reported to the regulator inside a day."
    files = {"file": ("notice.txt", io.BytesIO(content), "text/plain")}

    res = client.post("/api/analyze-file", files=files)

    assert res.status_code == 200
    data = res.json()
    assert called == [], "uploading a document must never trigger a web search"
    assert any("skipped web search" in s.lower() for s in data["status"])
    assert data["report"]["status"] != "insufficient_evidence"


def test_analyze_file_rejects_unsupported_extension():
    files = {"file": ("regulation.exe", io.BytesIO(b"binary"), "application/octet-stream")}
    res = client.post("/api/analyze-file", files=files)
    assert res.status_code == 400


def test_knowledge_endpoint_lists_demo_entries():
    res = client.get("/api/knowledge")
    assert res.status_code == 200
    entries = res.json()["entries"]
    assert len(entries) > 0
    assert all("type" in e and "title" in e and "source" in e for e in entries)
