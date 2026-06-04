from uuid import UUID


class UnsafeStoragePathError(ValueError):
    pass


def _safe_component(value: str, component_name: str) -> str:
    if not value or "/" in value or "\\" in value or value in {".", ".."} or ".." in value:
        raise UnsafeStoragePathError(f"Invalid storage path component: {component_name}")
    return value


def _safe_uuid(value: str, component_name: str) -> str:
    try:
        return str(UUID(str(value)))
    except ValueError as exc:
        raise UnsafeStoragePathError(f"Invalid UUID storage path component: {component_name}") from exc


def build_document_object_path(organization_id: str, document_id: str) -> str:
    return (
        f"organizations/{_safe_uuid(organization_id, 'organization_id')}"
        f"/documents/{_safe_uuid(document_id, 'document_id')}/original"
    )


def build_template_object_path(organization_id: str, occurrence_id: str, template_id: str) -> str:
    return (
        f"organizations/{_safe_uuid(organization_id, 'organization_id')}"
        f"/occurrences/{_safe_component(occurrence_id, 'occurrence_id')}"
        f"/templates/{_safe_component(template_id, 'template_id')}"
    )


def build_processing_artifact_object_path(
    organization_id: str,
    document_id: str,
    artifact_type: str,
    artifact_id: str,
) -> str:
    return (
        f"organizations/{_safe_uuid(organization_id, 'organization_id')}"
        f"/documents/{_safe_uuid(document_id, 'document_id')}"
        f"/artifacts/{_safe_component(artifact_type, 'artifact_type')}"
        f"/{_safe_component(artifact_id, 'artifact_id')}"
    )
