from collections.abc import Generator

from sqlalchemy.orm import Session

from app.core.database import get_db as session_dependency


def get_db() -> Generator[Session, None, None]:
    yield from session_dependency()
