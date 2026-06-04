"""create roles and permissions

Revision ID: 0003_create_roles_and_permissions
Revises: 0002_create_users_and_organizations
Create Date: 2026-06-04 00:00:00.000000
"""

from collections.abc import Sequence
from typing import Optional, Union
from uuid import NAMESPACE_URL, uuid5

import sqlalchemy as sa
from alembic import op

from app.permissions_catalog import PERMISSION_SEEDS, ROLE_PERMISSION_KEYS, ROLE_SEEDS


revision: str = "0003_create_roles_and_permissions"
down_revision: Optional[str] = "0002_create_users_and_organizations"
branch_labels: Optional[Union[str, Sequence[str]]] = None
depends_on: Optional[Union[str, Sequence[str]]] = None


def _seed_uuid(entity: str, key: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"mercadoia:{entity}:{key}"))


def _seed_roles_permissions(connection: sa.Connection) -> None:
    roles = sa.table(
        "roles",
        sa.column("id"),
        sa.column("key"),
        sa.column("name"),
        sa.column("scope"),
        sa.column("status"),
    )
    permissions = sa.table(
        "permissions",
        sa.column("id"),
        sa.column("key"),
        sa.column("name"),
        sa.column("scope"),
        sa.column("status"),
    )
    role_permissions = sa.table(
        "role_permissions",
        sa.column("id"),
        sa.column("role_id"),
        sa.column("permission_id"),
    )

    existing_role_keys = set(connection.execute(sa.select(roles.c.key)).scalars())
    missing_roles = [
        {
            "id": _seed_uuid("role", role.key),
            "key": role.key,
            "name": role.name,
            "scope": role.scope,
            "status": "active",
        }
        for role in ROLE_SEEDS
        if role.key not in existing_role_keys
    ]
    if missing_roles:
        connection.execute(roles.insert(), missing_roles)

    existing_permission_keys = set(connection.execute(sa.select(permissions.c.key)).scalars())
    missing_permissions = [
        {
            "id": _seed_uuid("permission", permission.key),
            "key": permission.key,
            "name": permission.name,
            "scope": permission.scope,
            "status": "active",
        }
        for permission in PERMISSION_SEEDS
        if permission.key not in existing_permission_keys
    ]
    if missing_permissions:
        connection.execute(permissions.insert(), missing_permissions)

    role_ids = dict(connection.execute(sa.select(roles.c.key, roles.c.id)).all())
    permission_ids = dict(connection.execute(sa.select(permissions.c.key, permissions.c.id)).all())
    existing_links = set(
        connection.execute(
            sa.select(role_permissions.c.role_id, role_permissions.c.permission_id)
        ).all()
    )

    missing_links = []
    for role_key, permission_keys in ROLE_PERMISSION_KEYS.items():
        role_id = role_ids[role_key]
        for permission_key in permission_keys:
            permission_id = permission_ids[permission_key]
            if (role_id, permission_id) in existing_links:
                continue
            missing_links.append(
                {
                    "id": _seed_uuid("role_permission", f"{role_key}:{permission_key}"),
                    "role_id": role_id,
                    "permission_id": permission_id,
                }
            )

    if missing_links:
        connection.execute(role_permissions.insert(), missing_links)


def upgrade() -> None:
    uuid_type = sa.Uuid(as_uuid=False)

    op.create_table(
        "roles",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_roles_key"),
    )
    op.create_index("ix_roles_scope", "roles", ["scope"])
    op.create_index("ix_roles_status", "roles", ["status"])

    op.create_table(
        "permissions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("scope", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_permissions_key"),
    )
    op.create_index("ix_permissions_scope", "permissions", ["scope"])
    op.create_index("ix_permissions_status", "permissions", ["status"])

    op.create_table(
        "role_permissions",
        sa.Column("id", uuid_type, nullable=False),
        sa.Column("role_id", uuid_type, nullable=False),
        sa.Column("permission_id", uuid_type, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"]),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_role_permission"),
    )
    op.create_index("ix_role_permissions_permission_id", "role_permissions", ["permission_id"])
    op.create_index("ix_role_permissions_role_id", "role_permissions", ["role_id"])

    with op.batch_alter_table("user_organizations") as batch_op:
        batch_op.add_column(sa.Column("role_id", uuid_type, nullable=True))
        batch_op.create_foreign_key(
            "fk_user_organizations_role_id",
            "roles",
            ["role_id"],
            ["id"],
        )

    op.create_index("ix_user_organizations_role_id", "user_organizations", ["role_id"])

    _seed_roles_permissions(op.get_bind())


def downgrade() -> None:
    op.drop_index("ix_user_organizations_role_id", table_name="user_organizations")
    with op.batch_alter_table("user_organizations") as batch_op:
        batch_op.drop_constraint("fk_user_organizations_role_id", type_="foreignkey")
        batch_op.drop_column("role_id")

    op.drop_index("ix_role_permissions_role_id", table_name="role_permissions")
    op.drop_index("ix_role_permissions_permission_id", table_name="role_permissions")
    op.drop_table("role_permissions")
    op.drop_index("ix_permissions_status", table_name="permissions")
    op.drop_index("ix_permissions_scope", table_name="permissions")
    op.drop_table("permissions")
    op.drop_index("ix_roles_status", table_name="roles")
    op.drop_index("ix_roles_scope", table_name="roles")
    op.drop_table("roles")
