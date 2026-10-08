from app.agents.clients import get_chat_model
from app.agents.prompts import VALIDATION_PROMPT
from app.agents.schemas import AnalysisDraft, ValidationResult
from app.agents.untrusted import encode_untrusted_json


class ValidationAgent:
    def invoke(self, draft: AnalysisDraft, evidence: list[dict]) -> ValidationResult:
        if not evidence and (draft.findings or draft.recommendations):
            return ValidationResult(
                accepted=False, limitations=["No supporting evidence was retrieved."]
            )

        for item in [*draft.findings, *draft.recommendations]:
            if not item.citations:
                return ValidationResult(
                    accepted=False,
                    limitations=["A material claim did not include a source citation."],
                )
            if any(
                not any(
                    citation.excerpt.casefold() in chunk["content"].casefold()
                    and citation.source_id == chunk["id"]
                    and citation.page == chunk["page_number"]
                    for chunk in evidence
                )
                for citation in item.citations
            ):
                return ValidationResult(
                    accepted=False,
                    limitations=["A citation excerpt could not be matched to retrieved evidence."],
                )

        validator = get_chat_model().with_structured_output(ValidationResult)
        return validator.invoke(
            [
                ("system", VALIDATION_PROMPT),
                (
                    "human",
                    "Proposed analysis and retrieved evidence are JSON data:\n"
                    + encode_untrusted_json(
                        {
                            "analysis": draft.model_dump(mode="json"),
                            "evidence": evidence,
                        }
                    ),
                ),
            ]
        )
