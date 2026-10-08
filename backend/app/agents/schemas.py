from pydantic import BaseModel, Field


class AnalysisPlan(BaseModel):
    questions: list[str] = Field(min_length=1, max_length=8)


class CitationDraft(BaseModel):
    source_id: str
    page: int | None = Field(default=None, ge=1)
    excerpt: str = Field(min_length=1)


class FindingDraft(BaseModel):
    title: str
    summary: str
    uncertainty: str | None = None
    citations: list[CitationDraft] = Field(default_factory=list)


class RecommendationDraft(BaseModel):
    summary: str
    rationale: str
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    citations: list[CitationDraft] = Field(default_factory=list)
    requires_approval: bool = True


class AnalysisDraft(BaseModel):
    findings: list[FindingDraft] = Field(default_factory=list)
    recommendations: list[RecommendationDraft] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    accepted: bool
    limitations: list[str] = Field(default_factory=list)


class AnswerDraft(BaseModel):
    answer: str
    citations: list[CitationDraft] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
