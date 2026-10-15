from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, UUID, uuid5

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.persistence.database import get_db
from app.persistence.models import Role, User

bearer = HTTPBearer(auto_error=False)
DEMO_ISSUER = "financial-analyst-demo"
DEMO_AUDIENCE = "financial-analyst-demo"
DEMO_ROLE_NAMES = {
    Role.ANALYST.value: "Guest Analyst",
    Role.APPROVER.value: "Guest Approver",
}


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    roles: frozenset[str]


def demo_mode_enabled(settings=None) -> bool:
    settings = settings or get_settings()
    return settings.demo_mode and settings.app_env in {"development", "test"}


def create_demo_token(role: str, settings=None) -> tuple[str, str, int]:
    settings = settings or get_settings()
    if not demo_mode_enabled(settings):
        raise ValueError("Demo login is not enabled.")
    if role not in DEMO_ROLE_NAMES:
        raise ValueError("Unsupported demo role.")
    now = int(datetime.now(UTC).timestamp())
    expires_in = 4 * 60 * 60
    user_id = uuid5(NAMESPACE_URL, f"financial-analyst-demo:{role}")
    claims = {
        "sub": str(user_id),
        "name": DEMO_ROLE_NAMES[role],
        "roles": [role],
        "demo": True,
        "iss": DEMO_ISSUER,
        "aud": DEMO_AUDIENCE,
        "iat": now,
        "exp": now + expires_in,
    }
    token = jwt.encode(
        claims,
        settings.demo_auth_secret.get_secret_value(),
        algorithm="HS256",
    )
    return token, DEMO_ROLE_NAMES[role], expires_in


def _decode_access_token(encoded_token: str, settings) -> tuple[UUID, frozenset[str], str]:
    algorithm = jwt.get_unverified_header(encoded_token).get("alg")
    if algorithm == "HS256":
        if not demo_mode_enabled(settings):
            raise ValueError("Demo login is not enabled.")
        claims = jwt.decode(
            encoded_token,
            settings.demo_auth_secret.get_secret_value(),
            algorithms=["HS256"],
            issuer=DEMO_ISSUER,
            audience=DEMO_AUDIENCE,
            options={"require": ["exp", "iat", "iss", "aud", "sub"]},
        )
        role_claim = claims.get("roles")
        if claims.get("demo") is not True or role_claim not in (
            [Role.ANALYST.value],
            [Role.APPROVER.value],
        ):
            raise ValueError("Invalid demo token.")
        role = role_claim[0]
        expected_id = uuid5(NAMESPACE_URL, f"financial-analyst-demo:{role}")
        if UUID(claims["sub"]) != expected_id:
            raise ValueError("Invalid demo identity.")
    elif algorithm == "RS256":
        if (
            not settings.jwt_public_key
            or not settings.jwt_public_key.get_secret_value().strip()
            or not settings.jwt_issuer
            or not settings.jwt_audience
        ):
            raise RuntimeError("Identity verification is not configured.")
        claims = jwt.decode(
            encoded_token,
            settings.jwt_public_key.get_secret_value(),
            algorithms=["RS256"],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
    else:
        raise ValueError("Unsupported access token algorithm.")

    user_id = UUID(claims["sub"])
    role_claim = claims.get("roles", [])
    if not isinstance(role_claim, list) or not all(isinstance(role, str) for role in role_claim):
        raise ValueError("Token roles must be a list of strings.")
    roles = frozenset(role_claim)
    if not roles.intersection({Role.ANALYST.value, Role.APPROVER.value}):
        raise PermissionError("No application role assigned.")
    return user_id, roles, str(claims.get("name", ""))[:255]


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: Session = Depends(get_db),
) -> CurrentUser:
    settings = get_settings()
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
        )
    try:
        user_id, roles, display_name = _decode_access_token(credentials.credentials, settings)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token.",
        ) from exc
    user = session.get(User, user_id)
    if user is None:
        user = User(
            id=user_id,
            display_name=display_name,
            roles=sorted(roles),
        )
        session.add(user)
    else:
        user.active = True
        user.display_name = display_name or user.display_name
        user.roles = sorted(roles)
    session.commit()
    return CurrentUser(id=user_id, roles=roles)


def require_role(role: Role):
    def dependency(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if role.value not in user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permission."
            )
        return user

    return dependency
