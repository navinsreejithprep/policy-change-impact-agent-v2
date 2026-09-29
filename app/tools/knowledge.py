"""OKF-style linked knowledge base access.

Each markdown file has YAML-ish frontmatter (type/title/owner) and a body
that links to related entries with standard markdown links. `search_knowledge`
finds candidate entries by keyword overlap; `expand_links` then walks the
markdown links one hop out so a hit on an Obligation or Process pulls in its
linked Policy/Control/Owner even if those files didn't match the keywords
directly. That link-following is what makes this "navigating linked
knowledge" rather than a flat keyword search.
"""
import re
from pathlib import Path

KB = Path(__file__).resolve().parents[1] / "knowledge"

_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+\.md)\)")

# Generic regulatory boilerplate ("must", "within", "hours"...) shows up in
# almost every obligation regardless of subject matter, so scoring on it
# drags in unrelated entries (a cyber-reporting deadline and a procurement
# threshold both say "must ... within"). Filtering it out lets the actual
# topical nouns (cyber, incidents, procurement, committee...) drive matches.
STOPWORDS = {
    "must", "shall", "require", "requires", "required", "mandatory", "mandates",
    "within", "hours", "days", "months", "years", "with", "that", "this", "these",
    "those", "from", "have", "will", "should", "also", "such", "only", "than",
    "then", "into", "under", "upon", "being", "been", "were", "which", "when",
    "where", "there", "their", "each", "every", "prior", "after", "before",
    "immediately", "effect", "force", "purpose", "person", "persons", "assess",
    "impact", "latest", "official", "find", "about", "your", "more",
}


def _parse(path: Path) -> tuple[dict, str]:
    text = path.read_text()
    frontmatter: dict = {}
    body = text
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            fm_text = text[3:end].strip()
            body = text[end + 3 :].strip()
            for line in fm_text.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    frontmatter[k.strip()] = v.strip()
    return frontmatter, body


def load_entry(path: Path) -> dict:
    fm, body = _parse(path)
    return {
        "id": path.stem,
        "path": str(path.relative_to(KB)),
        "type": fm.get("type", "Unknown"),
        "title": fm.get("title", path.stem),
        "owner": fm.get("owner"),
        "content": body,
        # "demo" = one of the hand-authored example entries shipped with the
        # project; "ingested" = came from a real document via /api/ingest.
        "source": fm.get("source", "demo"),
        "source_document": fm.get("source_document"),
    }


def read_frontmatter(path: Path) -> dict:
    fm, _ = _parse(path)
    return fm


def list_all_entries() -> list[dict]:
    """Every entry currently in the knowledge base (excluding the navigational
    index) — what /api/knowledge shows so it's never a black box."""
    return [
        load_entry(p)
        for p in KB.rglob("*.md")
        if read_frontmatter(p).get("type") not in _NON_EVIDENCE_TYPES
    ]


# The index is a navigational hub that links to every entry in the
# knowledge base. It must never be treated as evidence: matching it on a
# keyword (its table of contents mentions every topic) and then following
# its links would pull in every unrelated entry in the KB.
_NON_EVIDENCE_TYPES = {"KnowledgeIndex"}


def search_knowledge(query: str, limit: int = 8) -> list[dict]:
    terms = [t.lower() for t in re.findall(r"[A-Za-z0-9]{4,}", query)]
    terms = [t for t in terms if t not in STOPWORDS] or terms
    scored = []
    for p in KB.rglob("*.md"):
        fm, body = _parse(p)
        if fm.get("type") in _NON_EVIDENCE_TYPES:
            continue
        text = f"{fm.get('title', '')} {body}".lower()
        score = sum(text.count(t) for t in terms)
        if score:
            scored.append((score, p))
    scored.sort(key=lambda x: -x[0])
    return [load_entry(p) for _, p in scored[:limit]]


def expand_links(entries: list[dict], limit: int = 20) -> list[dict]:
    seen = {e["path"] for e in entries}
    result = list(entries)
    for e in list(entries):
        p = KB / e["path"]
        _, body = _parse(p)
        for m in _LINK_RE.finditer(body):
            rel = m.group(2)
            target = (p.parent / rel).resolve()
            if not target.exists():
                continue
            rel_to_kb = str(target.relative_to(KB))
            if rel_to_kb in seen:
                continue
            target_fm, _ = _parse(target)
            if target_fm.get("type") in _NON_EVIDENCE_TYPES:
                continue
            seen.add(rel_to_kb)
            result.append(load_entry(target))
            if len(result) >= limit:
                return result
    return result
