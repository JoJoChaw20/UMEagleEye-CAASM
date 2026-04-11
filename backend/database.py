import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()


def _build_database_url() -> str:
    postgres_db = os.getenv("POSTGRES_DB", "umeagleeye_db")
    postgres_user = os.getenv("POSTGRES_USER", "umeagleeye_admin")
    postgres_password = os.getenv("POSTGRES_PASSWORD", "S4cr3tP8ssw0rd")
    postgres_host = os.getenv("POSTGRES_HOST", "localhost")
    postgres_port = os.getenv("POSTGRES_PORT", "5432")
    return (
        f"postgresql+psycopg://{postgres_user}:{postgres_password}"
        f"@{postgres_host}:{postgres_port}/{postgres_db}"
    )


DATABASE_URL = os.getenv("DATABASE_URL", _build_database_url())

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

