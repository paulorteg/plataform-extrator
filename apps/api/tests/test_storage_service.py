from uuid import uuid4

import httpx
import pytest

from app.storage.paths import (
    UnsafeStoragePathError,
    build_document_object_path,
    build_processing_artifact_object_path,
)
from app.storage.service import SupabaseStorageService, build_storage_uri


def test_document_storage_path_requires_safe_uuid_components():
    organization_id = str(uuid4())
    document_id = str(uuid4())

    assert (
        build_document_object_path(organization_id, document_id)
        == f"organizations/{organization_id}/documents/{document_id}/original"
    )

    with pytest.raises(UnsafeStoragePathError):
        build_document_object_path("../bad", document_id)


def test_processing_artifact_path_rejects_traversal_components():
    with pytest.raises(UnsafeStoragePathError):
        build_processing_artifact_object_path(
            str(uuid4()),
            str(uuid4()),
            "../ocr",
            "payload",
        )


def test_supabase_storage_service_upload_signed_url_exists_and_delete(monkeypatch):
    calls = []
    service = SupabaseStorageService(
        supabase_url="https://example.supabase.co",
        service_role_key="test-service-role-key",
    )

    def fake_post(url, **kwargs):
        calls.append(("post", url, kwargs))
        if "/object/sign/" in url:
            return httpx.Response(200, json={"signedURL": "/object/sign/signed-token"})
        return httpx.Response(200, json={})

    def fake_head(url, **kwargs):
        calls.append(("head", url, kwargs))
        return httpx.Response(200)

    def fake_get(url, **kwargs):
        calls.append(("get", url, kwargs))
        return httpx.Response(200, content=b"stored-content")

    def fake_request(method, url, **kwargs):
        calls.append((method.lower(), url, kwargs))
        return httpx.Response(200, json={})

    monkeypatch.setattr(httpx, "post", fake_post)
    monkeypatch.setattr(httpx, "head", fake_head)
    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(httpx, "request", fake_request)

    storage_uri = service.upload(
        bucket="documents",
        object_path="organizations/org/documents/doc/original",
        content=b"content",
        content_type="application/pdf",
    )
    signed_url = service.create_signed_url(
        bucket="documents",
        object_path="organizations/org/documents/doc/original",
        expires_in=300,
    )
    exists = service.exists(
        bucket="documents",
        object_path="organizations/org/documents/doc/original",
    )
    downloaded = service.download(
        bucket="documents",
        object_path="organizations/org/documents/doc/original",
    )
    service.delete(
        bucket="documents",
        object_path="organizations/org/documents/doc/original",
    )

    assert storage_uri == build_storage_uri(
        "documents",
        "organizations/org/documents/doc/original",
    )
    assert signed_url == "https://example.supabase.co/storage/v1/object/sign/signed-token"
    assert exists is True
    assert downloaded == b"stored-content"
    assert [call[0] for call in calls] == ["post", "post", "head", "get", "delete"]
