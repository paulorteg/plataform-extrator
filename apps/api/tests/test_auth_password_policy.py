from app.db import models  # noqa: F401
from app.db.base import Base
from app.models.user import User


FORBIDDEN_USER_CREDENTIAL_FIELDS = {
    "hashed_password",
    "password",
    "password_digest",
    "password_hash",
    "senha",
    "senha_hash",
}


def test_users_model_does_not_define_password_or_hash_fields():
    user_columns = set(User.__table__.columns.keys())

    assert user_columns.isdisjoint(FORBIDDEN_USER_CREDENTIAL_FIELDS)


def test_registered_models_do_not_define_password_or_hash_fields():
    for table in Base.metadata.tables.values():
        column_names = set(table.columns.keys())
        assert column_names.isdisjoint(FORBIDDEN_USER_CREDENTIAL_FIELDS)
