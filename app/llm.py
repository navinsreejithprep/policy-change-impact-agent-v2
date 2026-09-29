import json
import re

from app.config import OPENAI_API_KEY, OPENAI_MODEL

_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def _extract_json(raw: str) -> str:
    text = _FENCE_RE.sub("", raw).strip()
    if text.startswith("{") or text.startswith("["):
        return text
    # last resort: grab the outermost {...} block
    start, end = text.find("{"), text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1]
    return text


def structured_call(prompt: str, fallback: dict) -> dict:
    """Calls the LLM and parses a JSON object response.

    Falls back to a deterministic, clearly-labelled value if no API key is
    configured or the call/parse fails for any reason — the workflow must
    keep working (with reduced fidelity) when OpenAI is unavailable.
    """
    if not OPENAI_API_KEY:
        return fallback
    try:
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            model=OPENAI_MODEL,
            api_key=OPENAI_API_KEY,
            temperature=0,
            model_kwargs={"response_format": {"type": "json_object"}},
        )
        response = llm.invoke(prompt + "\n\nRespond with a single JSON object only.")
        raw = response.content if isinstance(response.content, str) else str(response.content)
        return json.loads(_extract_json(raw))
    except Exception:
        return fallback
