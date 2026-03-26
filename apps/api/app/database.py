from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if "sqlite" in settings.DATABASE_URL:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def ensure_schema_compat() -> None:
    inspector = inspect(engine)
    if "segments" not in inspector.get_table_names():
        return

    columns = {column["name"] for column in inspector.get_columns("segments")}
    if "education_level" in columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE segments ADD COLUMN education_level VARCHAR"))
        connection.execute(text("UPDATE segments SET education_level = 'low' WHERE education_level IS NULL"))


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
