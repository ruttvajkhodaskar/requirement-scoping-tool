# Requirement & Scoping Tool

A small FastAPI service that reads a **customer call transcript or RFP text** and gives the estimating team:

1. A short summary
2. A list of requirements (dimensions, material, quantity, timeline, budget, standards)
3. A list of open questions (what is still missing)
4. A ready checklist in markdown
5. Optional: sends the notes to a CRM through a webhook

> **Demo version.** This is a clean rebuild for learning and showcase. It uses made-up sample data only. No company data or code is inside.

## Why I built it

After a discovery call, a sales rep has to turn messy notes into a scope that the estimating team can use. This often causes back-and-forth. This tool makes that handoff the same every time and shows what is missing right away.

## How it works

```
text (call / RFP)  ->  extract requirements  ->  summary + open questions
                                              ->  checklist for estimating
                                              ->  (optional) CRM webhook
```

Two modes:
- **LLM mode:** if `OPENAI_API_KEY` is set, LangChain asks an LLM for structured output (Pydantic schema). Works with any OpenAI-compatible API (set `OPENAI_BASE_URL`).
- **Rule mode:** with no key, simple keyword rules run, so you can try the project with nothing to set up.

## Run it

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # optional: add your key
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000/docs and try `POST /extract`.

Or with curl:

```bash
curl -X POST http://127.0.0.1:8000/extract \
  -H "Content-Type: application/json" \
  -d '{"text": "We need 500 pieces in stainless steel, 120 mm diameter, in 8 weeks."}'
```

Example output (rule mode):

```
Checklist
- [x] Dimensions: ...120 mm diameter...
- [x] Material: ...stainless steel...
- [x] Quantity: ...500 pieces...
- [x] Timeline: ...8 weeks
- [ ] Budget: MISSING - ask the customer
- [ ] Standards: MISSING - ask the customer
```

## Run tests

```bash
pytest -q
```

## Docker

```bash
docker build -t scoping-tool .
docker run -p 8000:8000 --env-file .env scoping-tool
```

## Project layout

```
app/
  main.py        FastAPI routes
  extractor.py   LLM mode + rule mode
  schemas.py     Pydantic models
  checklist.py   markdown checklist
  webhook.py     CRM webhook
samples/         made-up transcript and RFP
tests/           pytest tests
```

## Limits

- Rule mode is simple keyword matching. It can miss things. LLM mode is better but needs an API key and its output should still be checked by a person.
- Not tied to any real CRM. The webhook sends a JSON body to whatever URL you set.

## Tech

Python, FastAPI, LangChain, Pydantic, httpx, Docker, GitHub Actions, pytest
