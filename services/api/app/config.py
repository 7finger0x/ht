from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("HERMES_APP_NAME", "Hermes MVP API")
    service_name: str = os.getenv("HERMES_SERVICE_NAME", "hermes-api")
    environment: str = os.getenv("HERMES_ENVIRONMENT", "development")
    release_version: str = os.getenv("HERMES_RELEASE_VERSION", "development")
    source_commit: str = os.getenv("HERMES_SOURCE_COMMIT", "unknown")
    image_digest: str = os.getenv("HERMES_IMAGE_DIGEST", "unknown")
    log_level: str = os.getenv("HERMES_LOG_LEVEL", "INFO")
    api_bind: str = os.getenv("HERMES_API_BIND", "0.0.0.0:8000")
    api_reload: bool = os.getenv("HERMES_API_RELOAD", "false").lower() == "true"
    database_url: str = os.getenv(
        "HERMES_DATABASE_URL",
        "sqlite:///./services/api/hermes_mvp.db",
    )
    redis_url: str | None = os.getenv("HERMES_REDIS_URL")
    otlp_endpoint: str | None = os.getenv("HERMES_OTEL_EXPORTER_OTLP_ENDPOINT")
    metrics_enabled: bool = os.getenv("HERMES_METRICS_ENABLED", "true").lower() == "true"
    allowed_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv("HERMES_ALLOWED_ORIGINS", "http://localhost:5173").split(",")
        if origin.strip()
    )
    live_trading_enabled: bool = os.getenv("HERMES_LIVE_TRADING_ENABLED", "false").lower() == "true"
    auth_provider: str = os.getenv("HERMES_AUTH_PROVIDER", "dev-jwt")
    auth_jwt_algorithm: str = os.getenv("HERMES_AUTH_JWT_ALGORITHM", "HS256")
    auth_jwt_secret: str | None = os.getenv("HERMES_AUTH_JWT_SECRET")
    auth_public_key_pem: str | None = os.getenv("HERMES_AUTH_PUBLIC_KEY_PEM")
    auth_issuer: str | None = os.getenv("HERMES_AUTH_ISSUER")
    auth_audience: str | None = os.getenv("HERMES_AUTH_AUDIENCE") or os.getenv("HERMES_PRIVY_APP_ID")
    auth_clock_skew_seconds: int = int(os.getenv("HERMES_AUTH_CLOCK_SKEW_SECONDS", "30"))
    auth_principal_claim: str = os.getenv("HERMES_AUTH_PRINCIPAL_CLAIM", "principal_id")
    auth_tenant_claim: str = os.getenv("HERMES_AUTH_TENANT_CLAIM", "tenant_id")
    auth_roles_claim: str = os.getenv("HERMES_AUTH_ROLES_CLAIM", "roles")
    auth_scopes_claim: str = os.getenv("HERMES_AUTH_SCOPES_CLAIM", "scope")
    enable_dev_auth_bootstrap: bool = os.getenv("HERMES_ENABLE_DEV_AUTH_BOOTSTRAP", "false").lower() == "true"


settings = Settings()
