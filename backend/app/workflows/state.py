from typing import TypedDict


class AnalysisState(TypedDict, total=False):
    owner_id: str
    report_id: str
    report_text: str
    plan: dict
    evidence: list[dict]
    draft: dict
    validation: dict
    failed: bool
