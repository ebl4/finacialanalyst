from app.main import app


def test_application_exposes_report_and_human_approval_contracts() -> None:
    schema = app.openapi()
    paths = schema["paths"]

    assert "/api/v1/reports" in paths
    assert "/api/v1/approvals" in paths
    assert "/api/v1/recommendations/{recommendation_id}/decision" in paths
