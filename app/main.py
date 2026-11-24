import logging
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app import __version__, config
from app.checklist import build_checklist
from app.extractor import extract
from app.pdf import PdfError, extract_pdf_text
from app.schemas import ExtractRequest, ExtractResponse
from app.webhook import send_to_crm

logging.basicConfig(level=config.get("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("scoping.api")

app = FastAPI(
    title="Requirement & Scoping Tool",
    version=__version__,
    description="Turns call transcripts and RFPs into requirements, open questions and an estimating checklist.",
)

STATIC = Path(__file__).parent / "static"


def _run(text: str, customer: Optional[str], send_crm: bool, source: str) -> ExtractResponse:
    if not text.strip():
        raise HTTPException(status_code=400, detail="Text is empty.")
    if len(text) > config.MAX_TEXT_CHARS:
        raise HTTPException(status_code=413, detail=f"Text is too long (max {config.MAX_TEXT_CHARS} characters).")

    start = time.perf_counter()
    result, mode = extract(text)
    response = ExtractResponse(
        mode=mode,
        customer=customer,
        summary=result.summary,
        requirements=result.requirements,
        open_questions=result.open_questions,
        review_count=sum(r.needs_review for r in result.requirements),
        checklist=build_checklist(result),
    )
    if send_crm:
        response.crm = send_to_crm(response.model_dump(exclude={"crm"}))

    log.info(
        "extract source=%s mode=%s chars=%d reqs=%d review=%d crm=%s ms=%d",
        source, mode, len(text), len(result.requirements), response.review_count,
        response.crm, (time.perf_counter() - start) * 1000,
    )
    return response


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "version": __version__, "llm_configured": bool(config.get("OPENAI_API_KEY"))}


@app.post("/extract", response_model=ExtractResponse, response_model_exclude_none=True)
def extract_requirements(req: ExtractRequest):
    return _run(req.text, req.customer, req.send_to_crm, source="text")


@app.post("/extract-pdf", response_model=ExtractResponse, response_model_exclude_none=True)
async def extract_pdf(
    file: UploadFile = File(...),
    customer: Optional[str] = Form(None),
    send_to_crm: bool = Form(False),
):
    data = await file.read(config.MAX_PDF_BYTES + 1)
    if len(data) > config.MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="PDF is too large (max 10 MB).")
    try:
        text = extract_pdf_text(data)
    except PdfError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return _run(text, customer, send_to_crm, source=f"pdf:{file.filename}")
