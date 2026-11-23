import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./shift_bank.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 15} if "sqlite" in DATABASE_URL else {},
)

if "sqlite" in DATABASE_URL:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA busy_timeout = 5000")
        if ":memory:" not in DATABASE_URL:
            cursor.execute("PRAGMA journal_mode = WAL")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI database session dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
