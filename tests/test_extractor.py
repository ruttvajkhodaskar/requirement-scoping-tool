from pathlib import Path
from fastapi.testclient import TestClient
from app.extractor import extract_with_rules
from app.main import app

SAMPLES = Path(__file__).parent.parent / "samples"


def test_transcript_categories():
    text = (SAMPLES / "sample_transcript.txt").read_text()
    result = extract_with_rules(text)
    cats = {r.category for r in result.requirements}
    assert {"Quantity", "Material", "Dimensions", "Timeline", "Standards"} <= cats
    # Budget is not in the call, so it must show up as an open question
    assert any("budget" in q.lower() for q in result.open_questions)


def test_rfp_budget_found():
    text = (SAMPLES / "sample_rfp.txt").read_text()
    result = extract_with_rules(text)
    assert "Budget" in {r.category for r in result.requirements}


def test_api_extract(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = TestClient(app)
    r = client.post("/extract", json={"text": "We need 100 pieces in 4 weeks."})
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "rules"
    assert "Estimating Checklist" in body["checklist"]


def test_empty_text():
    client = TestClient(app)
    assert client.post("/extract", json={"text": "  "}).status_code == 400
