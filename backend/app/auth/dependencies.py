from dataclasses import dataclass
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.persistence.database import get_db
from app.persistence.models import Role, User

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    id: UUID
    roles: frozenset[str]


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    session: Session = Depends(get_db),
) -> CurrentUser:
    settings = get_settings()
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required."
        )
    if (
        not settings.jwt_public_key
        or not settings.jwt_public_key.get_secret_value().strip()
        or not settings.jwt_issuer
        or not settings.jwt_audience
    ):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Identity verification is not configured.",
        )
    try:
        claims = jwt.decode(
            credentials.credentials,
            settings.jwt_public_key.get_secret_value(),
            algorithms=["RS256"],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
        user_id = UUID(claims["sub"])
        role_claim = claims.get("roles", [])
        if not isinstance(role_claim, list) or not all(
            isinstance(role, str) for role in role_claim
        ):
            raise ValueError("Token roles must be a list of strings.")
        roles = frozenset(role_claim)
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token.",
        ) from exc
    if not roles.intersection({Role.ANALYST.value, Role.APPROVER.value}):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="No application role assigned."
        )
    user = session.get(User, user_id)
    if user is None:
        user = User(
            id=user_id,
            display_name=str(claims.get("name", ""))[:255],
            roles=sorted(roles),
        )
        session.add(user)
    else:
        user.active = True
        user.display_name = str(claims.get("name", user.display_name))[:255]
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
