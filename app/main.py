from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.graph.workflow import resume_analysis, start_analysis
from app.tools.document_ingest import extract_text, ingest_document
from app.tools.knowledge import list_all_entries

UI_DIR = Path(__file__).resolve().parent / "ui"
MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15 MB

app = FastAPI(title="Policy Change Impact Agent v2")


class AnalyzeRequest(BaseModel):
    user_input: str


class ConfirmRequest(BaseModel):
    thread_id: str
    action: str  # "confirm" | "search_again"


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    return start_analysis(req.user_input)


@app.post("/api/analyze-file")
async def analyze_file(file: UploadFile = File(...)):
    """Same as /api/analyze, but the regulation text comes from an uploaded
    document instead of pasted text — for when you have the actual circular/
    notification as a PDF/DOCX rather than copy-pasted text."""
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (15 MB limit).")
    try:
        text = extract_text(file.filename or "document", data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not text.strip():
        raise HTTPException(status_code=400, detail="No extractable text was found in the uploaded file.")
    # Uploading a document here is an unambiguous signal: it IS the
    # regulation to analyze, regardless of whether its extracted text
    # happens to contain the phrasing the free-text classifier looks for.
    return start_analysis(text, force_supplied=True)


@app.post("/api/confirm")
def confirm(req: ConfirmRequest):
    if req.action not in ("confirm", "search_again"):
        raise HTTPException(status_code=400, detail="action must be 'confirm' or 'search_again'")
    return resume_analysis(req.thread_id, req.action)


@app.get("/api/knowledge")
def knowledge():
    return {"entries": list_all_entries()}


@app.post("/api/ingest")
async def ingest(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (15 MB limit).")
    try:
        return ingest_document(file.filename or "document", data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


app.mount("/static", StaticFiles(directory=UI_DIR), name="static")


@app.get("/")
def index():
    return FileResponse(UI_DIR / "index.html")
