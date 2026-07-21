from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError

from .config import settings
from .observability import bind_authenticated_context


bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthContext:
    principal_id: str
    tenant_id: str
    roles: tuple[str, ...]
    scopes: tuple[str, ...]
    subject: str
    issuer: str | None
    audience: str | None


def require_authenticated_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthContext:
    return authenticate_request(request, credentials)


def require_scopes(*required_scopes: str):
    def dependency(
        request: Request,
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    ) -> AuthContext:
        context = authenticate_request(request, credentials)
        missing = [scope for scope in required_scopes if scope not in context.scopes]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "insufficient_scope",
                    "required_scopes": missing,
                },
            )
        return context

    return dependency


def authenticate_request(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> AuthContext:
    cached = getattr(request.state, "auth_context", None)
    if cached is not None:
        return cached

    if credentials is None:
        raise _unauthorized("missing_bearer_token")

    token = credentials.credentials.strip()
    if not token:
        raise _unauthorized("missing_bearer_token")

    try:
        payload = jwt.decode(
            token,
            key=_verification_key(),
            algorithms=[settings.auth_jwt_algorithm],
            audience=settings.auth_audience,
            issuer=settings.auth_issuer,
            leeway=settings.auth_clock_skew_seconds,
            options={
                "require": ["sub", settings.auth_tenant_claim],
                "verify_aud": settings.auth_audience is not None,
                "verify_iss": settings.auth_issuer is not None,
            },
        )
    except InvalidTokenError as exc:
        raise _unauthorized("invalid_token") from exc

    principal_id = _claim_as_string(payload, settings.auth_principal_claim) or _claim_as_string(payload, "sub")
    tenant_id = _claim_as_string(payload, settings.auth_tenant_claim)
    subject = _claim_as_string(payload, "sub")
    if principal_id is None or tenant_id is None or subject is None:
        raise _unauthorized("missing_required_claims")

    selected_tenant_id = _selected_tenant_id(request)
    if selected_tenant_id and selected_tenant_id != tenant_id:
        raise _forbidden("unauthorized_tenant_selection")

    context = AuthContext(
        principal_id=principal_id,
        tenant_id=selected_tenant_id or tenant_id,
        roles=_claim_as_tuple(payload, settings.auth_roles_claim),
        scopes=_claim_as_tuple(payload, settings.auth_scopes_claim),
        subject=subject,
        issuer=_claim_as_string(payload, "iss"),
        audience=_first_claim_value(payload.get("aud")),
    )
    request.state.auth_context = context
    bind_authenticated_context(context.principal_id, context.tenant_id)
    return context


def mint_development_token(
    *,
    principal_id: str,
    tenant_id: str,
    subject: str,
    roles: tuple[str, ...],
    scopes: tuple[str, ...],
    lifetime_seconds: int,
) -> dict[str, Any]:
    if not settings.enable_dev_auth_bootstrap:
        raise RuntimeError("Development auth bootstrap is disabled.")
    if not settings.auth_jwt_algorithm.startswith("HS"):
        raise RuntimeError("Development auth bootstrap requires an HS* JWT algorithm.")
    if not settings.auth_jwt_secret:
        raise RuntimeError("HERMES_AUTH_JWT_SECRET must be configured for development auth bootstrap.")

    issued_at = datetime.now(UTC)
    expires_at = issued_at + timedelta(seconds=max(60, min(lifetime_seconds, 86400)))
    payload = {
        "sub": subject,
        settings.auth_principal_claim: principal_id,
        settings.auth_tenant_claim: tenant_id,
        settings.auth_roles_claim: list(roles),
        settings.auth_scopes_claim: " ".join(scopes),
        "iss": settings.auth_issuer or "hermes-local-dev",
        "aud": settings.auth_audience or "hermes-local-dev",
        "iat": int(issued_at.timestamp()),
        "nbf": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.auth_jwt_secret, algorithm=settings.auth_jwt_algorithm)
    return {
        "access_token": token,
        "token_type": "Bearer",
        "expires_at": expires_at.isoformat(),
        "principal_id": principal_id,
        "tenant_id": tenant_id,
        "subject": subject,
        "roles": list(roles),
        "scopes": list(scopes),
    }


def _verification_key() -> str:
    if settings.auth_jwt_algorithm.startswith("HS"):
        if not settings.auth_jwt_secret:
            raise RuntimeError("HERMES_AUTH_JWT_SECRET must be configured for HS* token verification.")
        return settings.auth_jwt_secret

    if settings.auth_public_key_pem:
        return settings.auth_public_key_pem

    raise RuntimeError("HERMES_AUTH_PUBLIC_KEY_PEM must be configured for asymmetric token verification.")


def _selected_tenant_id(request: Request) -> str | None:
    value = request.headers.get("X-Hermes-Tenant-ID")
    if value is None:
        return None
    value = value.strip()
    return value or None


def _claim_as_string(payload: dict[str, Any], claim_name: str) -> str | None:
    value = payload.get(claim_name)
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return str(value)


def _claim_as_tuple(payload: dict[str, Any], claim_name: str) -> tuple[str, ...]:
    value = payload.get(claim_name)
    if value is None:
        return ()
    if isinstance(value, str):
        return tuple(item for item in (part.strip() for part in value.replace(",", " ").split()) if item)
    if isinstance(value, list):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return (str(value).strip(),) if str(value).strip() else ()


def _first_claim_value(value: Any) -> str | None:
    if isinstance(value, list):
        for item in value:
            text = str(item).strip()
            if text:
                return text
        return None
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _unauthorized(code: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"code": code},
        headers={"WWW-Authenticate": "Bearer"},
    )


def _forbidden(code: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"code": code},
    )
