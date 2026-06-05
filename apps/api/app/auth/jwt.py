from dataclasses import dataclass
import json
import time
from typing import Any
import urllib.request

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.auth.errors import AuthError


JWKS_CACHE_TTL_SECONDS = 600
JWKS_REQUEST_TIMEOUT_SECONDS = 5
JWKS_SUPPORTED_ALGORITHMS = frozenset({"ES256"})
LEGACY_SUPPORTED_ALGORITHMS = frozenset({"HS256"})
_JWKS_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


@dataclass(frozen=True)
class SupabaseTokenClaims:
    auth_user_id: str
    claims: dict[str, Any]


def _expected_issuer(supabase_url: str) -> str:
    return f"{supabase_url.rstrip('/')}/auth/v1"


def _jwks_url(supabase_url: str) -> str:
    return f"{_expected_issuer(supabase_url)}/.well-known/jwks.json"


def _fetch_jwks(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=JWKS_REQUEST_TIMEOUT_SECONDS) as response:
        return json.load(response)


def _get_cached_jwks(url: str) -> dict[str, Any]:
    now = time.monotonic()
    cached = _JWKS_CACHE.get(url)
    if cached is not None:
        expires_at, jwks = cached
        if expires_at > now:
            return jwks

    jwks = _fetch_jwks(url)
    _JWKS_CACHE[url] = (now + JWKS_CACHE_TTL_SECONDS, jwks)
    return jwks


def clear_jwks_cache() -> None:
    _JWKS_CACHE.clear()


def _get_jwks_key(token_header: dict[str, Any], supabase_url: str):
    algorithm = token_header.get("alg")
    key_id = token_header.get("kid")
    if algorithm not in JWKS_SUPPORTED_ALGORITHMS or not isinstance(key_id, str) or not key_id:
        raise AuthError(401, "invalid_token", "Invalid token.")

    jwks = _get_cached_jwks(_jwks_url(supabase_url))
    for jwk in jwks.get("keys", []):
        if jwk.get("kid") != key_id:
            continue
        if jwk.get("alg") != algorithm:
            continue
        try:
            return jwt.PyJWK.from_dict(jwk, algorithm=algorithm).key
        except Exception:
            raise AuthError(401, "invalid_token", "Invalid token.") from None

    raise AuthError(401, "invalid_token", "Invalid token.")


def _get_verification_key_and_algorithm(
    token: str,
    jwt_secret: str,
    supabase_url: str,
) -> tuple[Any, str]:
    try:
        token_header = jwt.get_unverified_header(token)
    except InvalidTokenError:
        raise AuthError(401, "invalid_token", "Invalid token.") from None

    algorithm = token_header.get("alg")
    if algorithm in LEGACY_SUPPORTED_ALGORITHMS:
        return jwt_secret, algorithm
    if algorithm in JWKS_SUPPORTED_ALGORITHMS:
        return _get_jwks_key(token_header, supabase_url), algorithm

    raise AuthError(401, "invalid_token", "Invalid token.")


def decode_supabase_jwt(token: str, jwt_secret: str, supabase_url: str) -> SupabaseTokenClaims:
    verification_key, algorithm = _get_verification_key_and_algorithm(
        token,
        jwt_secret,
        supabase_url,
    )
    try:
        claims = jwt.decode(
            token,
            verification_key,
            algorithms=[algorithm],
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
