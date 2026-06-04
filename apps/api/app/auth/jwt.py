from dataclasses import dataclass
from typing import Any

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.auth.errors import AuthError


@dataclass(frozen=True)
class SupabaseTokenClaims:
    auth_user_id: str
    claims: dict[str, Any]


def _expected_issuer(supabase_url: str) -> str:
    return f"{supabase_url.rstrip('/')}/auth/v1"


def decode_supabase_jwt(token: str, jwt_secret: str, supabase_url: str) -> SupabaseTokenClaims:
    try:
        claims = jwt.decode(
            token,
            jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
            issuer=_expected_issuer(supabase_url),
            options={"require": ["exp", "sub"]},
        )
    except ExpiredSignatureError:
        raise AuthError(401, "token_expired", "Token expired.") from None
    except InvalidTokenError:
        raise AuthError(401, "invalid_token", "Invalid token.") from None

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise AuthError(401, "invalid_token", "Invalid token.")

    return SupabaseTokenClaims(auth_user_id=subject, claims=claims)
