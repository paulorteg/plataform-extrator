from dataclasses import dataclass
from typing import Generator, Optional

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.errors import AuthError
from app.auth.jwt import SupabaseTokenClaims, decode_supabase_jwt
from app.core.config import get_settings
from app.models.user import User


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    user: User
    auth_user_id: str
    claims: dict


def get_database_session() -> Generator[Session, None, None]:
    from app.db.session import get_db

    yield from get_db()


def validate_bearer_token(
    credentials: Optional[HTTPAuthorizationCredentials],
) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthError(401, "missing_token", "Authentication required.")
    if not credentials.credentials:
        raise AuthError(401, "missing_token", "Authentication required.")
    return credentials.credentials


def get_token_claims(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> SupabaseTokenClaims:
    token = validate_bearer_token(credentials)
    settings = get_settings()
    return decode_supabase_jwt(token, settings.supabase_jwt_secret, settings.supabase_url)


def get_current_user(
    request: Request,
    token_claims: SupabaseTokenClaims = Depends(get_token_claims),
    db: Session = Depends(get_database_session),
) -> CurrentUser:
    user = db.execute(
        select(User).where(User.auth_user_id == token_claims.auth_user_id)
    ).scalar_one_or_none()

    if user is None:
        raise AuthError(403, "user_not_found", "User is not allowed.")

    if user.status != "active":
        raise AuthError(403, "user_inactive", "User is inactive.")

    current_user = CurrentUser(
        user=user,
        auth_user_id=token_claims.auth_user_id,
        claims=token_claims.claims,
    )
    request.state.current_user = current_user
    request.state.auth_user_id = token_claims.auth_user_id
    return current_user
