def build_document_object_path(organization_id: str, document_id: str) -> str:
    return f"organizations/{organization_id}/documents/{document_id}/original"


def build_template_object_path(organization_id: str, occurrence_id: str, template_id: str) -> str:
    return f"organizations/{organization_id}/occurrences/{occurrence_id}/templates/{template_id}"


def build_processing_artifact_object_path(
    organization_id: str,
    document_id: str,
    artifact_type: str,
    artifact_id: str,
) -> str:
    return f"organizations/{organization_id}/documents/{document_id}/artifacts/{artifact_type}/{artifact_id}"
