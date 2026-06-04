from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import models so Alembic and tests can discover table metadata.
from app.models.organization import Organization  # noqa: E402,F401
from app.models.user import User  # noqa: E402,F401
from app.models.user_organization import UserOrganization  # noqa: E402,F401
