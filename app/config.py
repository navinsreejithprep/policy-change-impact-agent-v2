import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")

DEFAULT_OFFICIAL_DOMAINS = {
    "cert-in.org.in",
    "meity.gov.in",
    "egazette.gov.in",
    "rbi.org.in",
    "sebi.gov.in",
    "irdai.gov.in",
    "pfrda.org.in",
    "mca.gov.in",
    "dot.gov.in",
    "pib.gov.in",
    "gov.in",
}

# Extra domains can be appended without code changes via a comma-separated env var.
_extra = os.getenv("ALLOWLIST_DOMAINS", "")
OFFICIAL_DOMAINS = DEFAULT_OFFICIAL_DOMAINS | {
    d.strip().lower() for d in _extra.split(",") if d.strip()
}

MAX_SOURCE_SEARCH_ATTEMPTS = int(os.getenv("MAX_SOURCE_SEARCH_ATTEMPTS", "3"))
MAX_EVIDENCE_ITERATIONS = int(os.getenv("MAX_EVIDENCE_ITERATIONS", "2"))
