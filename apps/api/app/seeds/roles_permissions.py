from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import Connection, insert, select

from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.permissions_catalog import PERMISSION_SEEDS, ROLE_PERMISSION_KEYS, ROLE_SEEDS


def _seed_uuid(entity: str, key: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"mercadoia:{entity}:{key}"))


def seed_roles_permissions(connection: Connection) -> None:
    role_table = Role.__table__
    permission_table = Permission.__table__
    role_permission_table = RolePermission.__table__

    existing_role_keys = set(connection.execute(select(role_table.c.key)).scalars())
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
        connection.execute(insert(role_table), missing_roles)

    existing_permission_keys = set(connection.execute(select(permission_table.c.key)).scalars())
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
        connection.execute(insert(permission_table), missing_permissions)

    role_ids = dict(connection.execute(select(role_table.c.key, role_table.c.id)).all())
    permission_ids = dict(connection.execute(select(permission_table.c.key, permission_table.c.id)).all())
    existing_links = set(
        connection.execute(
            select(role_permission_table.c.role_id, role_permission_table.c.permission_id)
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
        connection.execute(insert(role_permission_table), missing_links)


def main() -> None:
    from app.db.session import engine

    with engine.begin() as connection:
        seed_roles_permissions(connection)


if __name__ == "__main__":
    main()
