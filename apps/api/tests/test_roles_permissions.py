import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Permission, Role, RolePermission
from app.permissions_catalog import ROLE_PERMISSION_KEYS, all_permission_keys, all_role_keys
from app.seeds.roles_permissions import seed_roles_permissions


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


def test_seed_roles_permissions_is_idempotent(db_session):
    seed_roles_permissions(db_session.connection())
    db_session.commit()
    seed_roles_permissions(db_session.connection())
    db_session.commit()

    role_keys = set(db_session.execute(select(Role.key)).scalars())
    permission_keys = set(db_session.execute(select(Permission.key)).scalars())
    role_permission_count = db_session.execute(select(RolePermission)).all()

    assert role_keys == all_role_keys()
    assert permission_keys == all_permission_keys()
    assert len(role_permission_count) == sum(
        len(permission_keys) for permission_keys in ROLE_PERMISSION_KEYS.values()
    )


def test_role_permission_mapping_uses_registered_roles_and_permissions():
    registered_roles = all_role_keys()
    registered_permissions = all_permission_keys()

    assert set(ROLE_PERMISSION_KEYS) == registered_roles
    for permission_keys in ROLE_PERMISSION_KEYS.values():
        assert set(permission_keys).issubset(registered_permissions)


def test_roles_have_unique_keys(db_session):
    db_session.add(Role(key="viewer", name="Viewer", scope="organization", status="active"))
    db_session.flush()
    db_session.add(Role(key="viewer", name="Viewer Copy", scope="organization", status="active"))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_permissions_have_unique_keys(db_session):
    db_session.add(
        Permission(
            key="document_view",
            name="Document View",
            scope="organization",
            status="active",
        )
    )
    db_session.flush()
    db_session.add(
        Permission(
            key="document_view",
            name="Document View Copy",
            scope="organization",
            status="active",
        )
    )

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_role_permissions_do_not_duplicate_role_permission_pair(db_session):
    role = Role(key="auditor", name="Auditor", scope="organization", status="active")
    permission = Permission(
        key="audit_view",
        name="Audit View",
        scope="organization",
        status="active",
    )
    db_session.add_all([role, permission])
    db_session.flush()

    db_session.add(RolePermission(role_id=role.id, permission_id=permission.id))
    db_session.flush()
    db_session.add(RolePermission(role_id=role.id, permission_id=permission.id))

    with pytest.raises(IntegrityError):
        db_session.flush()


def test_platform_roles_do_not_get_sensitive_data_permissions_by_default(db_session):
    seed_roles_permissions(db_session.connection())
    db_session.commit()

    sensitive_permissions = {"sensitive_data_view", "sensitive_data_copy"}
    platform_roles = db_session.execute(
        select(Role).where(Role.key.in_(["platform_owner", "platform_admin"]))
    ).scalars()

    for role in platform_roles:
        permission_keys = {
            link.permission.key
            for link in db_session.execute(
                select(RolePermission).where(RolePermission.role_id == role.id)
            ).scalars()
        }
        assert permission_keys.isdisjoint(sensitive_permissions)


def test_role_scopes_distinguish_platform_and_organization_roles(db_session):
    seed_roles_permissions(db_session.connection())
    db_session.commit()

    role_scopes = dict(db_session.execute(select(Role.key, Role.scope)).all())

    assert role_scopes["platform_owner"] == "platform"
    assert role_scopes["platform_admin"] == "platform"
    assert role_scopes["organization_admin"] == "organization"
    assert role_scopes["manager"] == "organization"
    assert role_scopes["analyst"] == "organization"
    assert role_scopes["auditor"] == "organization"
    assert role_scopes["viewer"] == "organization"
