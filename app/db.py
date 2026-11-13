from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import DATABASE_URL

SCHEMA = "engine"  # keeps COIP tables apart from your Day 3-6 tables in `public`

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    metadata = MetaData(schema=SCHEMA)


def init_db(bind=None):
    from . import models  # noqa: F401  (registers the tables)

    bind = bind or engine
    with bind.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
        conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}"))
    Base.metadata.create_all(bind)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
