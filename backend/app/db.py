import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql+psycopg://contextos:contextos@localhost:5432/contextos"
)


class Base(DeclarativeBase):
    pass


def create_database_engine():
    """Create the engine at application startup, never during model imports."""
    return create_engine(DATABASE_URL, pool_pre_ping=True)


SessionLocal = sessionmaker(expire_on_commit=False)

