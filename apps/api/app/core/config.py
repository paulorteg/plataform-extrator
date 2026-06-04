from dataclasses import dataclass
from functools import lru_cache
import os


@dataclass(frozen=True)
class Settings:
    app_env: str
    supabase_db_url: str
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str
    supabase_jwt_secret: str
    supabase_storage_bucket_documents: str
    supabase_storage_bucket_templates: str
    supabase_storage_bucket_artifacts: str
    supabase_signed_url_ttl_seconds: int

    @property
    def database_url(self) -> str:
        return self.supabase_db_url


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _optional_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    return int(value)


def get_database_url() -> str:
    return _require_env("SUPABASE_DB_URL")


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_env=os.getenv("APP_ENV", "local"),
        supabase_db_url=get_database_url(),
        supabase_url=_require_env("SUPABASE_URL"),
        supabase_anon_key=_require_env("SUPABASE_ANON_KEY"),
        supabase_service_role_key=_require_env("SUPABASE_SERVICE_ROLE_KEY"),
        supabase_jwt_secret=_require_env("SUPABASE_JWT_SECRET"),
        supabase_storage_bucket_documents=_require_env("SUPABASE_STORAGE_BUCKET_DOCUMENTS"),
        supabase_storage_bucket_templates=_require_env("SUPABASE_STORAGE_BUCKET_TEMPLATES"),
        supabase_storage_bucket_artifacts=_require_env("SUPABASE_STORAGE_BUCKET_ARTIFACTS"),
        supabase_signed_url_ttl_seconds=_optional_int("SUPABASE_SIGNED_URL_TTL_SECONDS", 300),
    )
