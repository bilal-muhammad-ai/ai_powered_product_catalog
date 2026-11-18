from collections.abc import Generator
from datetime import datetime, timezone

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

engine = create_engine(get_settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@event.listens_for(Session, "before_flush")
def touch_updated_at(session: Session, _flush_context: object, _instances: object) -> None:
    now = datetime.now(timezone.utc)
    for obj in session.dirty:
        if hasattr(obj, "updated_at") and session.is_modified(obj, include_collections=False):
            obj.updated_at = now


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
