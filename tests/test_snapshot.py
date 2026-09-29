def test_snapshot_has_url_timestamp_and_hash(tmp_path, monkeypatch):
    import app.tools.snapshot_store as s

    monkeypatch.setattr(s, "SNAPSHOT_DIR", tmp_path)
    r = s.save_snapshot("https://example.gov/a", "hello", {"authority": "official"})
    assert r["url"] == "https://example.gov/a"
    assert r["content_hash"].startswith("sha256:")
    assert r["retrieved_at"]


def test_snapshot_hash_is_stable_for_same_content(tmp_path, monkeypatch):
    import app.tools.snapshot_store as s

    monkeypatch.setattr(s, "SNAPSHOT_DIR", tmp_path)
    r1 = s.save_snapshot("https://example.gov/a", "same content", {"authority": "official"})
    r2 = s.save_snapshot("https://example.gov/a", "same content", {"authority": "official"})
    assert r1["content_hash"] == r2["content_hash"]
    # retrieval timestamp of the first save is preserved, not overwritten
    assert r1["retrieved_at"] == r2["retrieved_at"]
    assert len(list(tmp_path.glob("*.json"))) == 1


def test_snapshot_hash_differs_for_different_content(tmp_path, monkeypatch):
    import app.tools.snapshot_store as s

    monkeypatch.setattr(s, "SNAPSHOT_DIR", tmp_path)
    r1 = s.save_snapshot("https://example.gov/a", "version one", {})
    r2 = s.save_snapshot("https://example.gov/a", "version two", {})
    assert r1["content_hash"] != r2["content_hash"]
