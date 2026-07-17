# --------------------------------------
# Database engine / session setup
# --------------------------------------

from urllib.parse import urlsplit, urlunsplit

import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from .config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Per-request DB session, closed once the request is done."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create the target database (e.g. dbhealthtracker) if it doesn't exist yet.
def ensure_database_exists() -> None:
    parts = urlsplit(settings.database_url)
    target_db = parts.path.lstrip("/")
    maintenance_url = urlunsplit((parts.scheme, parts.netloc, "/postgres", parts.query, parts.fragment))
    # psycopg2 doesn't understand the "postgresql+psycopg2://" SQLAlchemy
    # dialect prefix -- it accepts a plain "postgresql://" DSN.
    dsn = maintenance_url.replace("postgresql+psycopg2://", "postgresql://", 1)

    conn = psycopg2.connect(dsn)
    conn.autocommit = True  # CREATE DATABASE cannot run inside a transaction
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (target_db,))
            if cur.fetchone():
                return
            cur.execute(f'CREATE DATABASE "{target_db}"')
    finally:
        conn.close()
