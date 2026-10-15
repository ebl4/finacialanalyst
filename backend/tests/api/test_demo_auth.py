from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

import jwt
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.api.auth import DemoLoginRequest, demo_login, demo_login_status
from app.auth.dependencies import (
    DEMO_AUDIENCE,
    DEMO_ISSUER,
    _decode_access_token,
    create_demo_token,
)
from app.core.config import Settings
from app.persistence.models import Role

DEMO_SECRET = "test-demo-secret-that-is-at-least-32-characters"


def demo_settings(**overrides) -> Settings:
    values = {
        "app_env": "development",
        "demo_mode": True,
        "demo_auth_secret": DEMO_SECRET,
    }
    values.update(overrides)
    return Settings(**values)


def test_demo_mode_must_be_opted_in_and_not_enabled_in_production() -> None:
    with pytest.raises(ValidationError, match="only allowed"):
        demo_settings(app_env="production")
    with pytest.raises(ValidationError, match="at least 32 characters"):
        demo_settings(demo_auth_secret="short")
    assert Settings(app_env="development").demo_mode is False


def test_demo_login_creates_role_limited_short_lived_token(monkeypatch) -> None:
    settings = demo_settings()
    monkeypatch.setattr("app.api.auth.get_settings", lambda: settings)

    login = demo_login(DemoLoginRequest(role="analyst"))
    user_id, roles, name = _decode_access_token(login["access_token"], settings)

    assert login["display_name"] == "Guest Analyst"
    assert login["expires_in"] == 4 * 60 * 60
    assert user_id == uuid5(NAMESPACE_URL, f"financial-analyst-demo:{Role.ANALYST.value}")
    assert roles == frozenset({Role.ANALYST.value})
    assert name == "Guest Analyst"


def test_demo_login_status_and_endpoint_are_disabled_by_default(monkeypatch) -> None:
    settings = Settings(app_env="development")
    monkeypatch.setattr("app.api.auth.get_settings", lambda: settings)

    assert demo_login_status() == {"enabled": False}
    with pytest.raises(HTTPException) as error:
        demo_login(DemoLoginRequest(role="approver"))
    assert error.value.status_code == 404


def test_demo_token_cannot_escalate_role_or_be_used_after_demo_mode_is_disabled() -> None:
    settings = demo_settings()
    user_id = uuid5(NAMESPACE_URL, "financial-analyst-demo:analyst")
    now = int(datetime.now(UTC).timestamp())
    escalated = jwt.encode(
        {
            "sub": str(user_id),
            "roles": [Role.APPROVER.value],
            "demo": True,
            "iss": DEMO_ISSUER,
            "aud": DEMO_AUDIENCE,
            "iat": now,
            "exp": now + 14_400,
        },
        DEMO_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(ValueError, match="Invalid demo identity"):
        _decode_access_token(escalated, settings)
    with pytest.raises(ValueError, match="not enabled"):
        _decode_access_token(
            create_demo_token(Role.ANALYST.value, settings)[0],
            Settings(app_env="development"),
        )
