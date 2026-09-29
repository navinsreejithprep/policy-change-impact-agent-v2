# Policy Change Impact Agent v2

**Live:** https://policy-change-impact-agent-v2-production.up.railway.app
**Source:** https://github.com/navinsreejithprep/policy-change-impact-agent-v2

An agentic (not pipeline) regulatory-impact assistant: given a regulation — supplied
directly or described for discovery — it verifies the source, pauses for human
confirmation before anything consequential, walks a linked internal knowledge
graph (obligations → processes → policies → controls → owners), checks whether
the evidence it found is actually sufficient, loops back for more if not, and
only then produces an impact assessment.

**This is an analytical prototype. It is not legal advice, and it does not
file anything with a regulator.**

**"Our data" is whatever you've ingested — nothing more.** Out of the box, the
knowledge base (`app/knowledge/`) is a small hand-authored demo bundle
(a fictional incident-management process and a fictional procurement
process), not any real company's information. Upload a real policy, SOP, or
annual-report excerpt via the sidebar (or `POST /api/ingest`) to add real
entries — see [Ingesting real documents](#ingesting-real-documents) below.
`GET /api/knowledge` (and the sidebar panel) always shows exactly what's
currently in there, tagged `demo` or `ingested`, so it's never a black box.

## Why this is an agent, not a workflow

A fixed pipeline would be: search → scrape → summarize → done. This graph
instead makes real decisions at run time, using [LangGraph](https://langchain-ai.github.io/langgraph/)'s
`StateGraph` with conditional edges, a real `interrupt()`/`Command(resume=...)`
checkpoint (backed by a LangGraph checkpointer, not a boolean flag), and loops
that can re-run earlier steps:

- **Source authority branch** — a three-tier classification: `official`
  (curated allowlist, e.g. `cert-in.org.in`), `likely_official` (a generic
  government domain like `*.gov` or `*.gov.uk` not on the curated list), and
  `secondary` (blogs, news, law-firm commentary). Only the two government
  tiers proceed to confirmation; a `secondary` result is never silently
  trusted — the graph loops back to search again, excluding the domain it
  just rejected, up to a hard limit.
- **Human-in-the-loop branch** — even an official-looking source pauses the
  graph (`interrupt()`) and waits for an explicit `confirm` or `search_again`
  decision before any impact analysis happens. The graph is genuinely
  suspended mid-execution (checkpointed by thread id), not just showing a
  UI panel while continuing in the background.
- **Evidence sufficiency branch** — if the linked knowledge base doesn't
  produce a process, an owner, *and* a control for the requirement, the
  graph loops back to broaden the search, up to a hard limit, before
  admitting `Insufficient evidence` rather than guessing.
- **Terminal safety states** — both the "no authoritative source found" and
  "evidence too thin" paths are explicit dead ends that produce a clearly
  labeled report instead of forcing an answer.

## Architecture

```
app/
  config.py              env vars, official-domain allowlist (configurable)
  llm.py                 OpenAI call wrapper with deterministic fallback
  graph/
    state.py             AgentState TypedDict
    nodes.py              node functions (classify, search, version check,
                          human confirmation, extract, navigate OKF,
                          retrieve/check evidence, impact, final, insufficient)
    workflow.py           StateGraph wiring + start_analysis/resume_analysis
  tools/
    firecrawl_search.py   live web discovery (firecrawl-py v4 client)
    source_validator.py   allowlist check, draft/final detection, amendment flags
    snapshot_store.py     content-hash-addressed source snapshots
    knowledge.py          OKF-style linked knowledge base access
    injection_guard.py    prompt-injection pattern redaction + secret redaction
    document_ingest.py    real-document -> linked OKF-entry extraction pipeline
  knowledge/               the OKF-style bundle: obligations/processes/policies/
                            controls/owners, linked via markdown links
                            (source: demo | ingested, per entry's frontmatter)
  ui/                      vanilla HTML/CSS/JS single-page app
  main.py                  FastAPI app (/api/analyze, /api/confirm, /api/ingest,
                            /api/knowledge, static UI)
tests/                     pytest suite (see below)
snapshots/                 saved source snapshots (url, timestamp, sha-256, content)
```

### Graph shape

```
START → classify ─┬─ supplied → extract
                   └─ not supplied → firecrawl_search
                                        │
                              official source? ──no──→ (loop) firecrawl_search
                                        │ yes                    (up to N attempts,
                                        ▼                         then insufficient)
                                  version_check
                                        │
                               human_confirmation (interrupt)
                                confirm ──────┐   search_again → (loop) firecrawl_search
                                              ▼
                                           extract
                                              │
                                        navigate_okf
                                              │
                                      retrieve_evidence ──sufficient──→ impact → final → END
                                              │
                                        gaps found
                                              │
                                        more_evidence → (loop) retrieve_evidence
                                              │
                                     (limit reached) → insufficient → END
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env: OPENAI_API_KEY=..., FIRECRAWL_API_KEY=...
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000 — pick one of the example prompts in the sidebar, or
type your own.

### Environment variables

```text
OPENAI_API_KEY=            # optional — falls back to deterministic output if unset
OPENAI_MODEL=gpt-4o-mini
FIRECRAWL_API_KEY=         # optional — discovery returns no results if unset
ALLOWLIST_DOMAINS=         # optional, comma-separated, appended to the built-in list
MAX_SOURCE_SEARCH_ATTEMPTS=3
MAX_EVIDENCE_ITERATIONS=2
```

If `OPENAI_API_KEY` is missing, extraction and impact assessment fall back to
deterministic, clearly-labeled output instead of failing. If
`FIRECRAWL_API_KEY` is missing, discovery searches return no results (handled
as "no authoritative source found" rather than crashing) — supplying the
regulation text directly still works fully offline.

## Deployment

Deployed on [Railway](https://railway.app), not Vercel, deliberately: this
app depends on two things a serverless platform doesn't give you —

1. **In-memory human-confirmation state.** The `interrupt()`/`Command(resume=...)`
   checkpoint lives in the running Python process. Railway runs one
   persistent process, so the `/api/analyze` call and the later `/api/confirm`
   call reliably hit the same process. On Vercel's serverless functions, a
   second request can land on a different, memory-isolated instance, and the
   confirmation step would break unpredictably.
2. **Local file writes.** Document ingestion (`/api/ingest`) and source
   snapshots write to the container's local disk. Vercel's filesystem is
   read-only outside `/tmp`, and `/tmp` isn't shared across instances or
   persisted.

**Caveat that still applies on Railway:** the local filesystem persists for
the life of a running deployment, but a fresh deploy starts from a clean
checkout of the git repo — so anything ingested via `/api/ingest` (or any
saved snapshot) is lost on redeploy. That's fine for demo purposes; for
long-lived ingested knowledge, back it with a database or object storage
instead of local disk.

To redeploy after a code change (from this repo, with the Railway CLI linked):

```bash
railway up --detach
```

Environment variables are managed via `railway variable set KEY=value`
(never committed to the repo — `.env` is gitignored).

## Tests

```bash
pytest -q
```

The suite (26 tests) runs entirely offline against mocked Firecrawl/knowledge
calls and the LLM's deterministic fallback path — it never depends on live
web results, per the spec. It covers all of the mandatory checkpoints:

1. Supplied regulation skips Firecrawl entirely (`test_branching.py`)
2. Official source triggers human confirmation, then completes (`test_branching.py`)
3. Unofficial-only sources retry until the limit, then report insufficient
   evidence; a later official hit succeeds (`test_unofficial_source.py`)
4. Thin evidence loops back for more before giving up (`test_evidence_loop.py`)
5. Evidence still missing after the limit → `Insufficient evidence` (`test_evidence_loop.py`)
6. Prompt injection embedded in scraped content is detected, redacted, and
   never followed or leaked into output (`test_injection.py`)
7. Snapshots record url/timestamp/sha-256 and are stable/reproducible for
   identical content (`test_snapshot.py`)
8. A fully offline run from a saved snapshot, no network calls (`test_saved_source_offline.py`)

## Ingesting real documents

The bundled `app/knowledge/` folder is demo data only. To make the impact
assessment mean something for a real organization, upload real documents
(policies, SOPs, annual-report excerpts) — via the sidebar's upload control,
or directly:

```bash
curl -X POST http://127.0.0.1:8000/api/ingest -F "file=@/path/to/policy.pdf"
```

Supported formats: `.pdf`, `.docx`, `.txt`, `.md` (15 MB limit). What happens:

1. Text is extracted from the file.
2. It's sanitized as untrusted content (`injection_guard.py`) — the same
   defense used for scraped web pages, since a document could theoretically
   carry an injection attempt too.
3. It's split into bounded chunks (long documents are capped at 8 chunks to
   keep latency/cost sane) and sent to the LLM with an explicit instruction
   to extract only entries the text actually supports, categorized as
   Obligation/Process/Policy/Control/Owner, with references to other related
   entries by title (including ones already in the knowledge base, so a
   second document can link into the first).
4. Each extracted entry is written as a markdown file in the same
   frontmatter+markdown-link format as the demo entries, tagged
   `source: ingested` and `source_document: <filename>` — so the existing
   `navigate_okf`/`retrieve_evidence` nodes work on it completely unchanged.
   Re-ingesting the same document updates its own entries rather than piling
   up duplicates; it will never silently overwrite a hand-authored demo
   entry that happens to share a title.

`GET /api/knowledge` (and the sidebar panel) lists everything currently in
the knowledge base — every entry's type, title, and whether it's `demo` or
`ingested` (and from which file) — so you can always see exactly what the
agent is drawing on instead of trusting it blindly.

**Note:** entries are only as good as the LLM's extraction — always spot-check
what got written under `app/knowledge/<type>/*.md` after ingesting something
that matters, especially for a long or ambiguous document.

## Example queries

- **Supplied regulation:** `Material cyber incidents must be reported to the regulator within 24 hours.`
  → skips search, extracts the requirement, walks the incident-management
  knowledge chain, and (in the bundled demo knowledge base) finds a clean
  evidence trail with no gaps.
- **Discovery:** `Find the latest official CERT-In cyber security incident reporting requirement in India and assess its impact.`
  → searches live via Firecrawl, classifies candidates against the allowlist,
  checks version status, and pauses for your confirmation before analyzing.
- **Supplied regulation with a real mismatch:** `Purchases above ₹50 lakh require procurement committee approval.`
  → the bundled procurement knowledge base documents an internal
  committee-approval threshold of ₹75 lakh, so the impact assessment
  correctly flags the misalignment between the new rule and current practice.

## Guardrails in place

- Official-source allowlist (`app/config.py`, `ALLOWLIST_DOMAINS` env var) —
  unofficial candidates are never silently trusted.
- Draft vs. final vs. unknown version detection, plus a supersession/amendment
  flag surfaced in the confirmation panel.
- A genuine LangGraph `interrupt()` checkpoint before any impact analysis —
  not a UI-only confirmation.
- Scraped content is explicitly framed as untrusted data in every prompt, and
  `injection_guard.py` deterministically redacts common instruction-override
  patterns and secret-like strings before and after the LLM call.
- Hard iteration limits on both source search and evidence retrieval; both
  terminate in an explicit `Insufficient evidence` state rather than looping
  forever or guessing.
- The LLM is never the source of truth for facts — requirements/evidence are
  drawn from the supplied text, the scraped (and snapshotted) source, or the
  local knowledge base; the LLM is only used to extract/summarize/assess
  against that material, with deterministic fallbacks if it's unavailable.
