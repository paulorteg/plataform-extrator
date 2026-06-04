from dataclasses import dataclass


@dataclass(frozen=True)
class RoleSeed:
    key: str
    name: str
    scope: str


@dataclass(frozen=True)
class PermissionSeed:
    key: str
    name: str
    scope: str


ROLE_SEEDS: tuple[RoleSeed, ...] = (
    RoleSeed(key="platform_owner", name="Platform Owner", scope="platform"),
    RoleSeed(key="platform_admin", name="Platform Admin", scope="platform"),
    RoleSeed(key="organization_admin", name="Organization Admin", scope="organization"),
    RoleSeed(key="manager", name="Manager", scope="organization"),
    RoleSeed(key="analyst", name="Analyst", scope="organization"),
    RoleSeed(key="auditor", name="Auditor", scope="organization"),
    RoleSeed(key="viewer", name="Viewer", scope="organization"),
)


PERMISSION_SEEDS: tuple[PermissionSeed, ...] = (
    PermissionSeed(key="auth_login", name="Auth Login", scope="platform"),
    PermissionSeed(key="organization_view", name="Organization View", scope="organization"),
    PermissionSeed(key="user_invite", name="User Invite", scope="organization"),
    PermissionSeed(key="user_role_change", name="User Role Change", scope="organization"),
    PermissionSeed(key="plan_manage", name="Plan Manage", scope="platform"),
    PermissionSeed(key="package_assign", name="Package Assign", scope="platform"),
    PermissionSeed(key="usage_view", name="Usage View", scope="organization"),
    PermissionSeed(key="document_upload", name="Document Upload", scope="organization"),
    PermissionSeed(key="document_view", name="Document View", scope="organization"),
    PermissionSeed(key="document_download", name="Document Download", scope="organization"),
    PermissionSeed(key="occurrence_list", name="Occurrence List", scope="organization"),
    PermissionSeed(key="occurrence_view", name="Occurrence View", scope="organization"),
    PermissionSeed(key="review_field_edit", name="Review Field Edit", scope="organization"),
    PermissionSeed(key="review_field_approve", name="Review Field Approve", scope="organization"),
    PermissionSeed(key="review_approve_occurrence", name="Review Approve Occurrence", scope="organization"),
    PermissionSeed(key="template_generate", name="Template Generate", scope="organization"),
    PermissionSeed(key="template_download", name="Template Download", scope="organization"),
    PermissionSeed(key="sensitive_data_view", name="Sensitive Data View", scope="organization"),
    PermissionSeed(key="sensitive_data_copy", name="Sensitive Data Copy", scope="organization"),
    PermissionSeed(key="audit_view", name="Audit View", scope="organization"),
    PermissionSeed(key="audit_export", name="Audit Export", scope="organization"),
)


ROLE_PERMISSION_KEYS: dict[str, tuple[str, ...]] = {
    "platform_owner": (
        "auth_login",
        "organization_view",
        "user_invite",
        "user_role_change",
        "plan_manage",
        "package_assign",
        "usage_view",
        "audit_view",
        "audit_export",
    ),
    "platform_admin": (
        "auth_login",
        "organization_view",
        "plan_manage",
        "package_assign",
        "usage_view",
        "audit_view",
    ),
    "organization_admin": (
        "auth_login",
        "organization_view",
        "user_invite",
        "user_role_change",
        "usage_view",
        "document_upload",
        "document_view",
        "document_download",
        "occurrence_list",
        "occurrence_view",
        "review_field_edit",
        "review_field_approve",
        "review_approve_occurrence",
        "template_generate",
        "template_download",
        "sensitive_data_view",
        "sensitive_data_copy",
        "audit_view",
        "audit_export",
    ),
    "manager": (
        "auth_login",
        "organization_view",
        "usage_view",
        "document_view",
        "document_download",
        "occurrence_list",
        "occurrence_view",
        "review_field_approve",
        "review_approve_occurrence",
        "template_generate",
        "template_download",
        "sensitive_data_view",
        "audit_view",
    ),
    "analyst": (
        "auth_login",
        "organization_view",
        "document_upload",
        "document_view",
        "document_download",
        "occurrence_list",
        "occurrence_view",
        "review_field_edit",
        "review_field_approve",
        "template_generate",
        "template_download",
    ),
    "auditor": (
        "auth_login",
        "organization_view",
        "usage_view",
        "document_view",
        "document_download",
        "occurrence_list",
        "occurrence_view",
        "sensitive_data_view",
        "audit_view",
        "audit_export",
    ),
    "viewer": (
        "auth_login",
        "organization_view",
        "document_view",
        "occurrence_list",
        "occurrence_view",
        "template_download",
    ),
}


def all_role_keys() -> set[str]:
    return {role.key for role in ROLE_SEEDS}


def all_permission_keys() -> set[str]:
    return {permission.key for permission in PERMISSION_SEEDS}
