import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import CatalogueError
from app.core.text import retired_key, slugify
from app.models.category import Category
from app.models.product import Product
from app.schemas.category import CategoryCreate, CategoryNode, CategoryOut, CategoryUpdate
from app.services.category_lookup import descendants, get_category


def list_categories(db: Session) -> list[Category]:
    return list(
        db.scalars(
            select(Category).where(Category.deleted_at.is_(None)).order_by(Category.sort_order, Category.name)
        )
    )


def build_tree(rows: list[Category]) -> list[CategoryNode]:
    by_parent: dict[uuid.UUID | None, list[Category]] = {}
    for row in rows:
        by_parent.setdefault(row.parent_id, []).append(row)

    def build(parent_id: uuid.UUID | None) -> list[CategoryNode]:
        nodes: list[CategoryNode] = []
        for row in by_parent.get(parent_id, []):
            data = CategoryOut.model_validate(row).model_dump()
            nodes.append(CategoryNode(**data, children=build(row.id)))
        return nodes

    return build(None)


def _unique_slug(db: Session, base: str, exclude_id: uuid.UUID | None = None) -> str:
    slug = base
    number = 2
    while True:
        stmt = select(Category.id).where(Category.slug == slug)
        if exclude_id is not None:
            stmt = stmt.where(Category.id != exclude_id)
        if db.scalar(stmt) is None:
            return slug
        slug = f"{base}-{number}"
        number += 1


def _path_for(parent: Category | None, slug: str) -> str:
    if parent is None:
        return f"/{slug}/"
    return f"{parent.path}{slug}/"


def _rewrite_paths(db: Session, category: Category) -> None:
    children = list(
        db.scalars(
            select(Category).where(Category.parent_id == category.id, Category.deleted_at.is_(None))
        )
    )
    for child in children:
        child.path = _path_for(category, child.slug)
        _rewrite_paths(db, child)


def _assert_codes_fit(db: Session, category: Category) -> None:
    from app.services.attribute_schema import effective_attributes

    nodes = [category, *descendants(db, category)]
    for node in nodes:
        attributes = effective_attributes(db, node.id, active_only=False, include_inherited=True)
        codes = [attribute.code for attribute in attributes]
        if len(codes) != len(set(codes)):
            raise CatalogueError(
                f"This change would give {node.name} two attributes with the same code",
                409,
            )


def create_category(db: Session, data: CategoryCreate) -> Category:
    parent = get_category(db, data.parent_id) if data.parent_id else None
    base = slugify(data.slug or data.name)
    slug = _unique_slug(db, base)
    category = Category(
        name=data.name.strip(),
        slug=slug,
        parent_id=parent.id if parent else None,
        description=data.description,
        sort_order=data.sort_order,
        is_active=data.is_active,
        path=_path_for(parent, slug),
    )
    db.add(category)
    db.flush()
    return category


def update_category(db: Session, category: Category, data: CategoryUpdate) -> Category:
    changes = data.model_dump(exclude_unset=True)
    parent_changed = False
    if "name" in changes and changes["name"] is not None:
        category.name = changes["name"].strip()
    if "description" in changes:
        category.description = changes["description"]
    if "sort_order" in changes and changes["sort_order"] is not None:
        category.sort_order = changes["sort_order"]
    if "is_active" in changes and changes["is_active"] is not None:
        category.is_active = changes["is_active"]
    if "slug" in changes and changes["slug"]:
        slug = _unique_slug(db, slugify(changes["slug"]), exclude_id=category.id)
        if slug != category.slug:
            category.slug = slug
            parent = get_category(db, category.parent_id) if category.parent_id else None
            category.path = _path_for(parent, slug)
            _rewrite_paths(db, category)
    if "parent_id" in changes:
        new_parent_id = changes["parent_id"]
        if new_parent_id != category.parent_id:
            parent = get_category(db, new_parent_id) if new_parent_id else None
            if parent is not None and (parent.id == category.id or parent.path.startswith(category.path)):
                raise CatalogueError("A category cannot be moved under itself", 422)
            category.parent_id = parent.id if parent else None
            category.path = _path_for(parent, category.slug)
            _rewrite_paths(db, category)
            parent_changed = True
    db.flush()
    if parent_changed:
        _assert_codes_fit(db, category)
    return category


def delete_category(db: Session, category: Category) -> None:
    child = db.scalar(
        select(Category.id).where(Category.parent_id == category.id, Category.deleted_at.is_(None))
    )
    if child is not None:
        raise CatalogueError("Remove or move child categories before deleting this one", 409)
    product = db.scalar(
        select(Product.id).where(Product.category_id == category.id, Product.deleted_at.is_(None))
    )
    if product is not None:
        raise CatalogueError("This category still has products", 409)
    category.deleted_at = datetime.now(timezone.utc)
    category.slug = retired_key(category.slug, category.id, 180)
    category.path = f"/{category.slug}/"
    db.flush()


def to_node_list(db: Session) -> list[CategoryNode]:
    return build_tree(list_categories(db))


def to_out(category: Category) -> CategoryOut:
    return CategoryOut.model_validate(category)
