"""Live regulation discovery via Firecrawl.

Uses the firecrawl-py v4 unified client (`Firecrawl(...).search(...)`) with
scrape_options so each web result comes back with scraped markdown content,
not just a URL/title snippet — the extraction and version-check nodes need
real content, not a search snippet.

If FIRECRAWL_API_KEY is missing or the call fails for any reason, this
returns an empty list rather than raising, so the rest of the graph can
treat "no results" as a normal, handled case (see the Firecrawl-unavailable
edge case in the spec) instead of crashing the whole analysis.
"""
from app.config import FIRECRAWL_API_KEY
from app.tools.source_validator import classify_source


def _attr(item, name):
    if isinstance(item, dict):
        return item.get(name)
    return getattr(item, name, None)


def _meta_attr(item, name):
    meta = _attr(item, "metadata")
    if meta is None:
        return None
    if isinstance(meta, dict):
        return meta.get(name)
    return getattr(meta, name, None)


def firecrawl_search(query: str, limit: int = 6, exclude_domains: list[str] | None = None) -> list[dict]:
    if not FIRECRAWL_API_KEY:
        return []
    try:
        from firecrawl import Firecrawl
        from firecrawl.v2.types import ScrapeOptions

        client = Firecrawl(api_key=FIRECRAWL_API_KEY)
        kwargs = dict(
            sources=["web"],
            limit=limit,
            scrape_options=ScrapeOptions(formats=["markdown"], only_main_content=True),
        )
        if exclude_domains:
            kwargs["exclude_domains"] = exclude_domains
        result = client.search(query, **kwargs)
        items = getattr(result, "web", None) or []

        out = []
        for item in items:
            url = (
                _attr(item, "url")
                or _meta_attr(item, "source_url")
                or _meta_attr(item, "url")
            )
            if not url:
                continue
            title = _attr(item, "title") or _meta_attr(item, "title") or url
            content = _attr(item, "markdown") or _attr(item, "description") or ""
            out.append(
                {
                    "url": url,
                    "title": title,
                    "content": content,
                    "authority": classify_source(url),
                }
            )
        return out
    except Exception:
        return []
