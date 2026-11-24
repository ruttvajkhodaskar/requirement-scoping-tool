"""Pull requirements out of a call transcript or RFP text.

Modes
-----
llm            LangChain + structured output (needs OPENAI_API_KEY).
rules          Keyword/regex rules. Works with no API key.
rules-fallback The LLM call failed after retries, so rules were used instead.

Every requirement carries the sentence it came from, a confidence score, and a
needs_review flag. For LLM output the source sentence is checked against the
input text. If the model quoted something that is not in the text, the item is
flagged. This is the main guard against made-up requirements.
"""
import logging
import re
import time
from typing import List

from pydantic import BaseModel, Field

from app import config
from app.schemas import ALL_CATEGORIES, CATEGORIES, Requirement, ScopingResult

log = logging.getLogger("scoping.extractor")

CONFIDENT = 0.6  # below this, an item is flagged for review

# ---------- rule patterns ----------
_W = r"(?:one|two|three|four|five|six|seven|eight|nine|ten|twelve|fifteen|twenty|thirty|forty|fifty|hundred|thousand)"
NUM = r"(?:\d[\d,]*(?:\.\d+)?|" + _W + r"(?:[\s-]+" + _W + r")*)"
UNITS_Q = r"(?:pieces?|pcs|units?|nos|sets?)"
MONTHS = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)"

# category -> (strong pattern = a concrete value, weak pattern = only a keyword)
RULES = {
    "Dimensions": (
        r"(?i:\b\d+(?:\.\d+)?\s?(?:mm|cm|metres?|meters?|inch(?:es)?)\b)"
        r"|(?i:\b\d+(?:\.\d+)?\s?m\b)|±\s?\d|Ø\s?\d|(?i:plus[\s-]minus\s?\d)|\b(?:OD|ID)\s?\d",
        r"(?i:\b(?:diameter|length|width|height|thickness|tolerance|dimensions?)\b)",
    ),
    "Material": (
        r"(?i:\b(?:stainless|steel|aluminium|aluminum|copper|brass|bronze|titanium|zinc|plastic|abs|nylon"
        r"|rubber|polycarbonate|pvc|hdpe|cast iron|inconel|magnesium)\b)|(?i:\bss\s?\d{3}\b)",
        r"(?i:\b(?:material|grade|alloy)\b)",
    ),
    "Quantity": (
        r"(?i:\b" + NUM + r"\s?" + UNITS_Q + r"\b)|(?i:\b(?:qty|quantity)\.?\s*:?\s*\d)",
        r"(?i:\b(?:quantity|qty|volume|moq)\b)",
    ),
    "Timeline": (
        r"(?i:\b" + NUM + r"\s?(?:working days|business days|days|weeks?|months?)\b)"
        r"|(?i:\bby\s+(?:the\s+)?(?:end\s+of\s+)?(?:\d{1,2}(?:st|nd|rd|th)?\s+)?" + MONTHS + r"[a-z]*)"
        r"|(?i:\bQ[1-4]\b)|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"(?i:\b(?:deadline|delivery|lead time|turnaround|asap|due date|schedule)\b)",
    ),
    "Budget": (
        r"(?i:(?:₹|\$|€|\brs\.?|\binr|\busd|\beur)\s?\d)"
        r"|(?i:\b\d[\d,.]*\s?(?:lakhs?|crores?|rupees|dollars|k)\b)|(?i:\b(?:lakhs?|crores?)\b)",
        r"(?i:\b(?:budget|target price)\b)",
    ),
    "Standards": (
        r"\bASTM\s?[A-Z]?\d+|\b(?:ISO|DIN|BIS|IS|EN|JIS|IEC|ANSI|SAE)[\s:-]?\d{2,}|\b(?:RoHS|REACH)\b",
        r"(?i:\b(?:certified|certification|compliance|compliant|comply|standards?|inspection reports?)\b)",
    ),
}
COMPILED = {cat: (re.compile(s), re.compile(w)) for cat, (s, w) in RULES.items()}

QUESTIONS = {
    "Dimensions": "What are the exact dimensions and tolerances?",
    "Material": "Which material or grade is required?",
    "Quantity": "What is the order quantity (first order and yearly)?",
    "Timeline": "What is the delivery date or deadline?",
    "Budget": "Is there a budget or target price?",
    "Standards": "Are any standards or certifications required?",
}


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    cleaned = [p.strip(" -•*\t") for p in parts]
    return [p for p in cleaned if len(p) >= 6]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


# ---------- shared post-processing ----------
def finalize(result: ScopingResult, text: str, keep_summary: bool = False) -> ScopingResult:
    """Check sources, set review flags, rebuild open questions and the summary."""
    norm_text = _norm(text)
    for r in result.requirements:
        if r.category not in ALL_CATEGORIES:
            r.category = "Other"
        grounded = bool(r.source_sentence) and _norm(r.source_sentence) in norm_text
        if not grounded:
            r.confidence = min(r.confidence, 0.4)
        r.needs_review = r.confidence < CONFIDENT

    questions = list(result.open_questions)
    for cat in CATEGORIES:
        has_good = any(r.category == cat and not r.needs_review for r in result.requirements)
        if not has_good and QUESTIONS[cat] not in questions:
            questions.append(QUESTIONS[cat])
    result.open_questions = questions

    if not (keep_summary and result.summary.strip()):
        cats = {r.category for r in result.requirements if r.category in CATEGORIES and not r.needs_review}
        review = sum(r.needs_review for r in result.requirements)
        result.summary = (
            f"Found {len(result.requirements)} requirement(s). "
            f"{len(cats)} of {len(CATEGORIES)} categories are covered; {review} item(s) need review."
        )
    return result


# ---------- rule mode ----------
def extract_with_rules(text: str) -> ScopingResult:
    reqs, seen = [], set()
    for sentence in split_sentences(text):
        for cat, (strong, weak) in COMPILED.items():
            if strong.search(sentence):
                conf = 0.85
            elif weak.search(sentence):
                conf = 0.5
            else:
                continue
            if (cat, sentence) in seen:
                continue
            seen.add((cat, sentence))
            reqs.append(Requirement(category=cat, detail=sentence, source_sentence=sentence, confidence=conf))
    return finalize(ScopingResult(summary="", requirements=reqs, open_questions=[]), text)


# ---------- LLM mode ----------
class _LLMRequirement(BaseModel):
    category: str = Field(description="Dimensions, Material, Quantity, Timeline, Budget, Standards or Other")
    detail: str = Field(description="The requirement in one short sentence")
    source_sentence: str = Field(description="The exact sentence from the text, copied word for word")
    confidence: float = Field(description="0 to 1. Use a low value if the text is vague")


class _LLMResult(BaseModel):
    summary: str = Field(description="2-3 line summary of what the customer wants")
    requirements: List[_LLMRequirement]
    open_questions: List[str] = Field(description="Things that are missing or unclear")


SYSTEM_PROMPT = (
    "You help a pre-sales team. Read the customer text and extract engineering requirements. "
    "Use only what is in the text. Never invent numbers. "
    "Ignore facts about the customer's own company or past orders unless they are requirements for this order. "
    "For every requirement, copy the exact source sentence from the text. "
    "Categories: Dimensions, Material, Quantity, Timeline, Budget, Standards, Other. "
    "Give a low confidence when the text is vague. List missing or unclear things as open questions."
)


def _call_llm(text: str) -> _LLMResult:
    """One attempt. LangChain is imported here so rule mode works without it."""
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI

    llm = ChatOpenAI(
        model=config.get("LLM_MODEL", "gpt-4o-mini"),
        base_url=config.get("OPENAI_BASE_URL") or None,
        temperature=0,
        timeout=30,
    ).with_structured_output(_LLMResult)
    prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("human", "{text}")])
    return (prompt | llm).invoke({"text": text})


def extract_with_llm(text: str) -> ScopingResult:
    attempts = int(config.get("LLM_MAX_RETRIES", "2")) + 1
    last_error = None
    for i in range(attempts):
        try:
            raw = _call_llm(text)
            reqs = [Requirement(**r.model_dump()) for r in raw.requirements]
            result = ScopingResult(summary=raw.summary, requirements=reqs, open_questions=raw.open_questions)
            return finalize(result, text, keep_summary=True)
        except Exception as e:  # network, rate limit, bad output
            last_error = e
            log.warning("LLM attempt %d/%d failed: %s", i + 1, attempts, e)
            if i < attempts - 1:
                time.sleep(float(config.get("LLM_RETRY_DELAY", "1")) * (2 ** i))
    raise RuntimeError(f"LLM failed after {attempts} attempts: {last_error}")


# ---------- entry point ----------
def extract(text: str) -> tuple[ScopingResult, str]:
    if config.get("OPENAI_API_KEY"):
        try:
            return extract_with_llm(text), "llm"
        except RuntimeError as e:
            log.error("%s. Falling back to rules.", e)
            return extract_with_rules(text), "rules-fallback"
    return extract_with_rules(text), "rules"
