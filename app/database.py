from sqlalchemy import create_engine  # type: ignore
from sqlalchemy.ext.declarative import declarative_base  # type: ignore
from sqlalchemy.orm import sessionmaker  # type: ignore
from sqlalchemy import text  # type: ignore
from sqlalchemy.exc import OperationalError  # type: ignore
from dotenv import load_dotenv
from pathlib import Path
import os

env_path = Path('.') / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)

DATABASE_URL = os.getenv("DATABASE_URL")
print(f"Using DATABASE_URL: {DATABASE_URL}")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Please configure it in the environment or .env file.")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_db_connection() -> None:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except OperationalError as exc:
        raise RuntimeError(
            "Database connection failed. Check DATABASE_URL credentials and PostgreSQL availability."
        ) from exc

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()