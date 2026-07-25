from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# SQLite (the local-dev default) hands out connections that are bound to the
# creating thread, which breaks under FastAPI's threadpool for sync routes.
# Postgres needs neither this flag nor tolerates it.
_connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,   # checks if the connection is alive before using it
    pool_recycle=300,     # refreshes connections every 5 minutes to avoid stale ones
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()