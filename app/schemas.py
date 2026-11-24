from typing import List, Optional
from pydantic import BaseModel, Field

CATEGORIES = ["Dimensions", "Material", "Quantity", "Timeline", "Budget", "Standards"]


class Requirement(BaseModel):
    category: str = Field(description="One of: Dimensions, Material, Quantity, Timeline, Budget, Standards, Other")
    detail: str = Field(description="The requirement in one short sentence")


class ScopingResult(BaseModel):
    summary: str = Field(description="2-3 line summary of what the customer wants")
    requirements: List[Requirement]
    open_questions: List[str] = Field(description="Things still missing or unclear")


class ExtractRequest(BaseModel):
    text: str
    customer: Optional[str] = None
    send_to_crm: bool = False
