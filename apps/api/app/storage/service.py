from dataclasses import dataclass
from typing import Optional, Protocol

import httpx

from app.core.config import Settings, get_settings


class StorageError(Exception):
    pass


class StorageObjectNotFoundError(StorageError):
    pass


class StorageService(Protocol):
    def upload(
        self,
        *,
        bucket: str,
        object_path: str,
        content: bytes,
        content_type: str,
    ) -> str:
        ...

    def create_signed_url(self, *, bucket: str, object_path: str, expires_in: int) -> str:
        ...

    def delete(self, *, bucket: str, object_path: str) -> None:
        ...

    def exists(self, *, bucket: str, object_path: str) -> bool:
        ...

    def download(self, *, bucket: str, object_path: str) -> bytes:
        ...


def build_storage_uri(bucket: str, object_path: str) -> str:
    return f"supabase://{bucket}/{object_path}"


@dataclass(frozen=True)
class SupabaseStorageService:
    supabase_url: str
    service_role_key: str
    timeout_seconds: float = 15.0

    @classmethod
    def from_settings(cls, settings: Optional[Settings] = None) -> "SupabaseStorageService":
        resolved_settings = settings or get_settings()
        return cls(
            supabase_url=resolved_settings.supabase_url.rstrip("/"),
            service_role_key=resolved_settings.supabase_service_role_key,
        )

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.service_role_key}",
            "apikey": self.service_role_key,
        }

    def upload(
        self,
        *,
        bucket: str,
        object_path: str,
        content: bytes,
        content_type: str,
    ) -> str:
        url = f"{self.supabase_url}/storage/v1/object/{bucket}/{object_path}"
        headers = {**self._headers, "Content-Type": content_type, "x-upsert": "false"}
        response = httpx.post(url, content=content, headers=headers, timeout=self.timeout_seconds)
        if response.status_code >= 400:
            raise StorageError("Storage upload failed.")
        return build_storage_uri(bucket, object_path)

    def create_signed_url(self, *, bucket: str, object_path: str, expires_in: int) -> str:
        url = f"{self.supabase_url}/storage/v1/object/sign/{bucket}/{object_path}"
        response = httpx.post(
            url,
            json={"expiresIn": expires_in},
            headers=self._headers,
            timeout=self.timeout_seconds,
        )
        if response.status_code >= 400:
            raise StorageError("Storage signed URL creation failed.")
        payload = response.json()
        signed_url = payload.get("signedURL") or payload.get("signedUrl") or payload.get("url")
        if not signed_url:
            raise StorageError("Storage signed URL response is invalid.")
        if signed_url.startswith("http://") or signed_url.startswith("https://"):
            return signed_url
        return f"{self.supabase_url}/storage/v1{signed_url}"

    def delete(self, *, bucket: str, object_path: str) -> None:
        url = f"{self.supabase_url}/storage/v1/object/{bucket}"
        response = httpx.request(
            "DELETE",
            url,
            json={"prefixes": [object_path]},
            headers=self._headers,
            timeout=self.timeout_seconds,
        )
        if response.status_code >= 400:
            raise StorageError("Storage delete failed.")

    def exists(self, *, bucket: str, object_path: str) -> bool:
        url = f"{self.supabase_url}/storage/v1/object/{bucket}/{object_path}"
        response = httpx.head(url, headers=self._headers, timeout=self.timeout_seconds)
        if response.status_code == 404:
            return False
        if response.status_code >= 400:
            raise StorageError("Storage exists check failed.")
        return True

    def download(self, *, bucket: str, object_path: str) -> bytes:
        url = f"{self.supabase_url}/storage/v1/object/{bucket}/{object_path}"
        response = httpx.get(url, headers=self._headers, timeout=self.timeout_seconds)
        if response.status_code == 404:
            raise StorageObjectNotFoundError("Storage object not found.")
        if response.status_code >= 400:
            raise StorageError("Storage download failed.")
        return response.content
