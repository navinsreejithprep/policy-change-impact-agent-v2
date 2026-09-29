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
