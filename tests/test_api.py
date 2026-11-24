import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app import webhook
from app.main import app
from tests.helpers import make_pdf

client = TestClient(app)


@pytest.fixture(autouse=True)
def no_llm(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("CRM_WEBHOOK_URL", raising=False)


def test_health():
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["llm_configured"] is False


def test_home_page():
    r = client.get("/")
    assert r.status_code == 200 and "Requirement" in r.text


def test_extract_text():
    r = client.post("/extract", json={"text": "We need 100 pieces in 4 weeks.", "customer": "Acme"})
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "rules" and body["customer"] == "Acme"
    assert "Estimating Checklist" in body["checklist"]
    assert body["requirements"][0]["source_sentence"]


def test_empty_text_rejected():
    assert client.post("/extract", json={"text": "  "}).status_code == 400
    assert client.post("/extract", json={"text": ""}).status_code == 422


def test_too_long_text_rejected():
    assert client.post("/extract", json={"text": "a" * 50_001}).status_code == 422


def test_pdf_upload():
    pdf = make_pdf(["Quantity: 800 pieces.", "Material is brass.", "Delivery in 6 weeks."])
    r = client.post("/extract-pdf", files={"file": ("rfp.pdf", pdf, "application/pdf")})
    assert r.status_code == 200
    got = {x["category"] for x in r.json()["requirements"]}
    assert {"Quantity", "Material", "Timeline"} <= got


def test_sample_pdf_file():
    from pathlib import Path
    pdf = (Path(__file__).parent.parent / "samples" / "sample_rfp.pdf").read_bytes()
    r = client.post("/extract-pdf", files={"file": ("sample_rfp.pdf", pdf, "application/pdf")})
    assert r.status_code == 200
    got = {x["category"] for x in r.json()["requirements"] if not x["needs_review"]}
    assert {"Quantity", "Material", "Dimensions", "Timeline", "Budget", "Standards"} <= got


def test_pdf_rejects_non_pdf():
    r = client.post("/extract-pdf", files={"file": ("x.pdf", b"hello", "application/pdf")})
    assert r.status_code == 422 and "not a PDF" in r.json()["detail"]


def test_pdf_without_text():
    pdf = make_pdf([])
    r = client.post("/extract-pdf", files={"file": ("blank.pdf", pdf, "application/pdf")})
    assert r.status_code == 422 and "scanned" in r.json()["detail"]


def test_crm_skipped_without_url():
    r = client.post("/extract", json={"text": "We need 100 pieces.", "send_to_crm": True})
    assert r.json()["crm"].startswith("skipped")


def test_crm_signature_and_retry(monkeypatch):
    monkeypatch.setenv("CRM_WEBHOOK_URL", "https://crm.example/hook")
    monkeypatch.setenv("CRM_WEBHOOK_SECRET", "s3cret")
    monkeypatch.setattr(webhook.time, "sleep", lambda s: None)
    seen = []

    def fake_post(url, content, headers, timeout):
        seen.append((content, headers))
        return httpx.Response(503 if len(seen) < 2 else 200, request=httpx.Request("POST", url))

    monkeypatch.setattr(webhook.httpx, "post", fake_post)
    r = client.post("/extract", json={"text": "We need 100 pieces.", "send_to_crm": True})
    assert r.json()["crm"] == "sent (200)" and len(seen) == 2
    body, headers = seen[-1]
    assert headers["X-Signature"] == webhook.sign(body, "s3cret")
    assert json.loads(body)["mode"] == "rules"


def test_crm_client_error_not_retried(monkeypatch):
    monkeypatch.setenv("CRM_WEBHOOK_URL", "https://crm.example/hook")
    calls = []

    def fake_post(url, content, headers, timeout):
        calls.append(1)
        return httpx.Response(401, request=httpx.Request("POST", url))

    monkeypatch.setattr(webhook.httpx, "post", fake_post)
    assert webhook.send_to_crm({"a": 1}) == "failed (HTTP 401)" and len(calls) == 1
