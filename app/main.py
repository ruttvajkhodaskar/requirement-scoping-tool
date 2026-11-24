from fastapi import FastAPI, HTTPException
from app.schemas import ExtractRequest
from app.extractor import extract
from app.checklist import build_checklist
from app.webhook import send_to_crm

app = FastAPI(title="Requirement & Scoping Tool")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/extract")
def extract_requirements(req: ExtractRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="text is empty")

    result, mode = extract(req.text)
    checklist = build_checklist(result)

    response = {
        "mode": mode,
        "customer": req.customer,
        "summary": result.summary,
        "requirements": [r.model_dump() for r in result.requirements],
        "open_questions": result.open_questions,
        "checklist": checklist,
    }
    if req.send_to_crm:
        response["crm"] = send_to_crm(response)
    return response
