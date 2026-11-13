"""Database settings. Reads the repo's root .env (the same one docker compose uses),
so there is nothing extra to configure. Set DATABASE_URL to override."""
import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")  # when .env sits next to app/


def _build_url() -> str:
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    user = os.getenv("POSTGRES_USER", "postgres")
    password = quote_plus(os.getenv("POSTGRES_PASSWORD", "postgres"))
    db = os.getenv("POSTGRES_DB", "postgres")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"


DATABASE_URL = _build_url()
