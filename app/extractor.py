"""Pull requirements out of a call transcript or RFP text.

Two modes:
1. LLM mode  - used when OPENAI_API_KEY is set (LangChain + structured output).
2. Rule mode - simple keyword rules, so the demo runs with no API key.
"""
import os
import re
from app.schemas import CATEGORIES, Requirement, ScopingResult

RULES = {
    "Dimensions": r"\b\d+(\.\d+)?\s?(mm|cm|m|inch|inches|in)\b|\bdiameter\b|\blength\b|\bthickness\b",
    "Material": r"\b(steel|stainless|aluminium|aluminum|copper|brass|plastic|abs|nylon|rubber|cast iron)\b",
    "Quantity": r"\b\d[\d,]*\s?(units|pcs|pieces|nos|sets|parts)\b|\bquantity\b",
    "Timeline": r"\b\d+\s?(days|weeks|months)\b|\bdeadline\b|\bdelivery\b|\bby\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*",
    "Budget": r"(₹|\$|rs\.?|inr|usd)\s?\d|\bbudget\b",
    "Standards": r"\b(iso|astm|din|bis|is)\s?[-:]?\s?\d+\b|\bcertified\b|\bcompliance\b",
}

QUESTIONS = {
    "Dimensions": "What are the exact dimensions and tolerances?",
    "Material": "Which material or grade is required?",
    "Quantity": "What is the order quantity (first order and yearly)?",
    "Timeline": "What is the delivery date or deadline?",
    "Budget": "Is there a budget or target price?",
    "Standards": "Are any standards or certifications required?",
}


def _sentences(text: str):
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip(" -•\t") for p in parts if len(p.strip()) > 8]


def extract_with_rules(text: str) -> ScopingResult:
    reqs, seen = [], set()
    for sentence in _sentences(text):
        for cat, pattern in RULES.items():
            if re.search(pattern, sentence, re.IGNORECASE) and (cat, sentence) not in seen:
                seen.add((cat, sentence))
                reqs.append(Requirement(category=cat, detail=sentence))
    found = {r.category for r in reqs}
    questions = [QUESTIONS[c] for c in CATEGORIES if c not in found]
    summary = f"Found {len(reqs)} requirement(s) across {len(found)} of {len(CATEGORIES)} categories."
    return ScopingResult(summary=summary, requirements=reqs, open_questions=questions)


def extract_with_llm(text: str) -> ScopingResult:
    # Imported here so the rule mode works even if LangChain is not installed.
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        base_url=os.getenv("OPENAI_BASE_URL") or None,
        temperature=0,
    ).with_structured_output(ScopingResult)

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "You help a pre-sales team. Read the customer text and extract engineering requirements. "
         "Use only what is in the text. Do not invent numbers. "
         "Categories: Dimensions, Material, Quantity, Timeline, Budget, Standards, Other. "
         "List anything missing or unclear as open questions."),
        ("human", "{text}"),
    ])
    return (prompt | llm).invoke({"text": text})


def extract(text: str) -> tuple[ScopingResult, str]:
    if os.getenv("OPENAI_API_KEY"):
        return extract_with_llm(text), "llm"
    return extract_with_rules(text), "rules"
