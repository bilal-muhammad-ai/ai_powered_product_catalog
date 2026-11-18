import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import CatalogueError
from app.models.category import Category


def get_category(db: Session, category_id: uuid.UUID) -> Category:
    category = db.get(Category, category_id)
    if category is None or category.deleted_at is not None:
        raise CatalogueError("Category not found", 404)
    return category


def descendants(db: Session, category: Category) -> list[Category]:
    return list(
        db.scalars(
            select(Category).where(
                Category.path.startswith(category.path),
                Category.id != category.id,
                Category.deleted_at.is_(None),
            )
        )
    )
