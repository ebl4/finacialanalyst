from app.agents.clients import get_chat_model
from app.agents.prompts import ANALYSIS_PROMPT
from app.agents.schemas import AnalysisDraft
from app.agents.untrusted import encode_untrusted_json


def format_evidence(chunks: list[dict]) -> str:
    return encode_untrusted_json(
        [
            {
                "source_id": chunk["id"],
                "report_id": chunk.get("report_id"),
                "knowledge_source_id": chunk.get("knowledge_source_id"),
                "page_number": chunk.get("page_number"),
                "content": chunk["content"],
            }
            for chunk in chunks
        ],
    )


class AnalysisAgent:
    def invoke(self, task: str, evidence: str) -> AnalysisDraft:
        analyst = get_chat_model().with_structured_output(AnalysisDraft)
        return analyst.invoke(
            [
                ("system", ANALYSIS_PROMPT),
                ("human", f"Analysis questions:\n{task}\n\nAuthorized evidence:\n{evidence}"),
            ]
        )
