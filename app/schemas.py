from typing import List, Optional
from pydantic import BaseModel, Field

CATEGORIES = ["Dimensions", "Material", "Quantity", "Timeline", "Budget", "Standards"]
ALL_CATEGORIES = CATEGORIES + ["Other"]


class Requirement(BaseModel):
    category: str = Field(description="Dimensions, Material, Quantity, Timeline, Budget, Standards or Other")
    detail: str = Field(description="The requirement in one short sentence")
    source_sentence: str = Field("", description="Exact sentence copied from the input text")
    confidence: float = Field(0.5, ge=0, le=1)
    needs_review: bool = Field(False, description="True when a person should check this item")


class ScopingResult(BaseModel):
    summary: str
    requirements: List[Requirement]
    open_questions: List[str]


class ExtractRequest(BaseModel):
    text: str = Field(min_length=1, max_length=50_000)
    customer: Optional[str] = Field(None, max_length=200)
    send_to_crm: bool = False


class ExtractResponse(BaseModel):
    mode: str = Field(description="llm, rules, or rules-fallback (LLM failed)")
    customer: Optional[str] = None
    summary: str
    requirements: List[Requirement]
    open_questions: List[str]
    review_count: int
    checklist: str
    crm: Optional[str] = None
