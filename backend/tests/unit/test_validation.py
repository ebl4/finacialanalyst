from app.agents.schemas import AnalysisDraft, FindingDraft, RecommendationDraft
from app.agents.validation import ValidationAgent


def test_validation_rejects_material_finding_without_citations() -> None:
    draft = AnalysisDraft(
        findings=[FindingDraft(title="Revenue", summary="Revenue increased.")],
    )

    result = ValidationAgent().invoke(
        draft, [{"id": "chunk", "page_number": 1, "content": "Revenue"}]
    )

    assert result.accepted is False
    assert "citation" in result.limitations[0]


def test_validation_rejects_citation_from_wrong_source_or_page() -> None:
    draft = AnalysisDraft(
        findings=[
            FindingDraft(
                title="Revenue",
                summary="Revenue increased.",
                citations=[
                    {
                        "source_id": "wrong-chunk",
                        "page": 2,
                        "excerpt": "Revenue increased",
                    }
                ],
            )
        ]
    )

    result = ValidationAgent().invoke(
        draft, [{"id": "source-chunk", "page_number": 1, "content": "Revenue increased"}]
    )

    assert result.accepted is False
    assert "citation excerpt" in result.limitations[0]


def test_recommendations_default_to_human_review() -> None:
    recommendation = RecommendationDraft(
        summary="Review the exposure",
        rationale="The report shows concentration risk.",
    )

    assert recommendation.requires_approval is True
