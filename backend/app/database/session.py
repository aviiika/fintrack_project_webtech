from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from app.config import settings

ca = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=ca, echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

class Base(DeclarativeBase): pass

def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try: yield db
    finally: db.close()

def init_db():
    from app.models import (  # noqa: F401
        budget, import_log, transaction, user, correction_counter,
        stock_holding, liability, networth_snapshot,
    )
    Base.metadata.create_all(bind=engine)
