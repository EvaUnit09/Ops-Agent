""""Database enginer and sessions etup, shared by all routers"""

import os
from collections.abc import Generator
from sqlalchemy import create_engine

from sqlalchemy.orm import DeclarativeBase, Session, session, sessionmaker

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://ops_agent:ops_agent@db:5432/ops_agent"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    """ Base class for all ORM models (Asset, User, Checkout) """

def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a request-scoped DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()