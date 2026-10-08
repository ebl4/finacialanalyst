from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    status: str
    submitted_at: datetime
    error: str | None = None


class CitationResponse(BaseModel):
    source_id: UUID
    chunk_id: UUID | None = None
    label: str
    page: int | None = None
    excerpt: str | None = None


class FindingResponse(BaseModel):
    id: UUID
    title: str
    summary: str
    uncertainty: str | None
    citations: list[CitationResponse]


class RecommendationResponse(BaseModel):
    id: UUID
    summary: str
    rationale: str
    assumptions: list[str]
    limitations: list[str]
    sensitivity: str
    status: str
    citations: list[CitationResponse]
    decisions: list[dict] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    report_id: UUID
    status: str
    findings: list[FindingResponse]
    recommendations: list[RecommendationResponse]
    limitations: list[str] = []


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


class AnswerResponse(BaseModel):
    answer: str
    citations: list[CitationResponse]
    limitations: list[str]


class DecisionRequest(BaseModel):
    outcome: str
    reason: str | None = None
