import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.enums import ProductStatus
from app.schemas.common import Page
from app.schemas.product import ProductDetail, ProductListItem, ProductWrite
from app.services import products as product_service

router = APIRouter(prefix="/products", tags=["products"])


@router.get("", response_model=Page[ProductListItem])
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    category_id: uuid.UUID | None = None,
    status_filter: ProductStatus | None = Query(default=None, alias="status"),
    attr: list[str] = Query(default_factory=list),
    db: Session = Depends(get_db),
) -> Page[ProductListItem]:
    items, total = product_service.list_products(
        db,
        page=page,
        page_size=page_size,
        q=q,
        category_id=category_id,
        status=status_filter,
        attr_filters=product_service.parse_attr_filters(attr),
    )
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=ProductDetail, status_code=status.HTTP_201_CREATED)
def create_product(data: ProductWrite, db: Session = Depends(get_db)) -> ProductDetail:
    return product_service.to_detail(product_service.save_product(db, data))


@router.get("/{product_id}", response_model=ProductDetail)
def get_product(product_id: uuid.UUID, db: Session = Depends(get_db)) -> ProductDetail:
    return product_service.to_detail(product_service.get_product(db, product_id))


@router.patch("/{product_id}", response_model=ProductDetail)
def update_product(product_id: uuid.UUID, data: ProductWrite, db: Session = Depends(get_db)) -> ProductDetail:
    product = product_service.get_product(db, product_id)
    return product_service.to_detail(product_service.save_product(db, data, product))


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    product_service.delete_product(db, product_service.get_product(db, product_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
