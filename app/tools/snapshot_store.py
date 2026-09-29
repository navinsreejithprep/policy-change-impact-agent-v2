import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

SNAPSHOT_DIR = Path(__file__).resolve().parents[2] / "snapshots"
SNAPSHOT_DIR.mkdir(exist_ok=True)


def save_snapshot(url: str, content: str, metadata: dict | None = None) -> dict:
    """Saves a source snapshot keyed by content hash.

    Identical content (even if re-scraped later, or re-scraped from a
    different candidate URL that happens to serve the same text) produces
    the same file and the original retrieval timestamp is preserved, so
    repeated runs are reproducible rather than constantly rewriting new
    "latest" timestamps.
    """
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    path = SNAPSHOT_DIR / f"{digest[:16]}.json"
    record = {
        "url": url,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "content_hash": f"sha256:{digest}",
        "authority": (metadata or {}).get("authority", "unknown"),
        "version_status": (metadata or {}).get("version_status", "unknown"),
        "content": content,
    }
    if path.exists():
        existing = json.loads(path.read_text())
        record["retrieved_at"] = existing.get("retrieved_at", record["retrieved_at"])
    path.write_text(json.dumps(record, indent=2))
    return record


def load_snapshot(digest_or_path) -> dict:
    p = Path(digest_or_path)
    if not p.is_absolute():
        p = SNAPSHOT_DIR / p
    return json.loads(p.read_text())
