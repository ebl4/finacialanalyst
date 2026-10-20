from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException, UploadFile
from pydantic import SecretStr

from app.api.reports import submit_report
from app.auth.dependencies import CurrentUser


class FakeSession:
    def __init__(self) -> None:
        self.events = []

    def add(self, entity) -> None:
        self.events.append(("add", entity))

    def flush(self) -> None:
        self.events.append(("flush", None))

    def commit(self) -> None:
        self.events.append(("commit", None))


class FakeStorage:
    def put(self, key: str, body: bytes, content_type: str) -> None:
        self.upload = (key, body, content_type)


@pytest.mark.asyncio
async def test_submit_report_persists_report_before_analysis_run(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.reports.get_settings",
        lambda: SimpleNamespace(
            max_upload_bytes=1024,
            ai_provider="openai",
            openai_api_key=SecretStr("test-key"),
            google_api_key=None,
        ),
    )
    session = FakeSession()
    storage = FakeStorage()
    user = CurrentUser(id=uuid4(), roles=frozenset({"analyst"}))
    upload = UploadFile(
        filename="annual-report.pdf",
        file=BytesIO(b"%PDF-content"),
        headers={"content-type": "application/pdf"},
    )

    response = await submit_report(file=upload, user=user, session=session, storage=storage)

    assert [event[0] for event in session.events] == ["add", "flush", "add", "commit"]
    report = session.events[0][1]
    run = session.events[2][1]
    assert report.id == run.report_id == response["id"]
    assert storage.upload[1:] == (b"%PDF-content", "application/pdf")


@pytest.mark.asyncio
async def test_submit_report_rejects_upload_when_selected_provider_key_is_missing(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "app.api.reports.get_settings",
        lambda: SimpleNamespace(
            max_upload_bytes=1024,
            ai_provider="gemini",
            openai_api_key=SecretStr("unused-openai-key"),
            google_api_key=None,
        ),
    )
    session = FakeSession()
    storage = FakeStorage()
    upload = UploadFile(
        filename="annual-report.pdf",
        file=BytesIO(b"%PDF-content"),
        headers={"content-type": "application/pdf"},
    )

    with pytest.raises(HTTPException) as error:
        await submit_report(
            file=upload,
            user=CurrentUser(id=uuid4(), roles=frozenset({"analyst"})),
            session=session,
            storage=storage,
        )

    assert error.value.status_code == 503
    assert "GOOGLE_API_KEY" in error.value.detail
    assert session.events == []
    assert not hasattr(storage, "upload")


@pytest.mark.asyncio
async def test_submit_report_accepts_gemini_without_openai_key(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.api.reports.get_settings",
        lambda: SimpleNamespace(
            max_upload_bytes=1024,
            ai_provider="gemini",
            openai_api_key=None,
            google_api_key=SecretStr("test-google-key"),
        ),
    )
    session = FakeSession()
    storage = FakeStorage()
    upload = UploadFile(
        filename="annual-report.pdf",
        file=BytesIO(b"%PDF-content"),
        headers={"content-type": "application/pdf"},
    )

    response = await submit_report(
        file=upload,
        user=CurrentUser(id=uuid4(), roles=frozenset({"analyst"})),
        session=session,
        storage=storage,
    )

    assert response["status"] == "queued"
    assert [event[0] for event in session.events] == ["add", "flush", "add", "commit"]
