from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.auth.dependencies import create_demo_token, demo_mode_enabled
from app.core.config import get_settings

router = APIRouter(tags=["authentication"])


class DemoLoginRequest(BaseModel):
    role: Literal["analyst", "approver"]


@router.get("/auth/demo")
def demo_login_status() -> dict[str, bool]:
    return {"enabled": demo_mode_enabled()}


@router.post("/auth/demo")
def demo_login(request: DemoLoginRequest) -> dict[str, str | int]:
    settings = get_settings()
    if not demo_mode_enabled(settings):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demo login is not enabled.",
        )
    token, display_name, expires_in = create_demo_token(request.role, settings)
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_in": expires_in,
        "display_name": display_name,
        "role": request.role,
    }
