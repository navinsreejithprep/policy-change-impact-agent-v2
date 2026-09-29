from urllib.parse import urlparse

from app.config import OFFICIAL_DOMAINS

# Generic government-domain patterns, for jurisdictions not on the curated
# allowlist. A hit here is "likely_official" rather than "official" — a
# lower-confidence tier that still reaches human confirmation (the human
# makes the final call) instead of being discarded outright like a blog or
# law-firm commentary post would be.
GENERIC_OFFICIAL_SUFFIXES = (
    ".gov",
    ".gov.uk",
    ".gov.au",
    ".govt.nz",
    ".gc.ca",
    ".go.jp",
    ".go.kr",
    ".gouv.fr",
    ".europa.eu",
    ".gov.sg",
    ".gov.hk",
    ".gov.za",
    ".admin.ch",
    ".nic.in",
)

DRAFT_MARKERS = [
    "draft",
    "consultation paper",
    "exposure draft",
    "proposed rule",
    "for public comments",
    "invites comments",
]

FINAL_MARKERS = [
    "notified",
    "gazette",
    "comes into force",
    "with immediate effect",
    "final circular",
    "notification no",
    "in exercise of the powers",
]

SUPERSESSION_MARKERS = [
    "supersede",
    "superseded",
    "repeal",
    "amended by",
    "amendment to",
    "stands withdrawn",
]


def domain_of(url: str) -> str:
    return urlparse(url).netloc.lower().split(":")[0]


def is_official(url: str) -> bool:
    d = domain_of(url)
    if not d:
        return False
    return d in OFFICIAL_DOMAINS or any(d.endswith("." + x) for x in OFFICIAL_DOMAINS)


def is_likely_official(url: str) -> bool:
    d = domain_of(url)
    if not d:
        return False
    return any(d == suf.lstrip(".") or d.endswith(suf) for suf in GENERIC_OFFICIAL_SUFFIXES)


def classify_source(url: str) -> str:
    """Three-tier authority classification.

    "official"        — on the curated allowlist (app/config.py); highest
                         confidence, e.g. cert-in.org.in, *.gov.in.
    "likely_official"  — matches a generic government-domain pattern
                         (*.gov, *.gov.uk, *.europa.eu, ...) but isn't on the
                         curated list. Still reaches human confirmation
                         rather than being auto-trusted or auto-rejected.
    "secondary"        — everything else (blogs, law firms, news, forums).
                         Never auto-accepted; triggers another search.
    """
    if is_official(url):
        return "official"
    if is_likely_official(url):
        return "likely_official"
    return "secondary"


def detect_version_status(content: str, title: str = "") -> str:
    text = f"{title} {content}".lower()
    if any(m in text for m in DRAFT_MARKERS):
        return "draft"
    if any(m in text for m in FINAL_MARKERS):
        return "final"
    return "unknown"


def detect_amendment_note(content: str) -> str | None:
    text = content.lower()
    for marker in SUPERSESSION_MARKERS:
        if marker in text:
            return (
                f"Source text references '{marker}' — verify this is the current "
                "version before relying on it; an amendment or supersession may apply."
            )
    return None
