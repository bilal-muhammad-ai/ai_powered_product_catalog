import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.order.enums import OrderStatus
from app.schemas.common import Page
from app.schemas.order.order import OrderCatalogHit, OrderItemIn, OrderListItem, OrderOut, OrderWrite
from app.services.order import catalog as catalog_service
from app.services.order import orders as order_service

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/catalog", response_model=list[OrderCatalogHit])
def order_catalog(
    q: str | None = None,
    category_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
) -> list[OrderCatalogHit]:
    return catalog_service.search_catalog(db, q=q, category_id=category_id)


@router.get("", response_model=Page[OrderListItem])
def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    status_filter: OrderStatus | None = Query(default=None, alias="status"),
    date_from: date | None = None,
    date_to: date | None = None,
    sort: str = Query("order_date"),
    direction: str = Query("desc"),
    db: Session = Depends(get_db),
) -> Page[OrderListItem]:
    items, total = order_service.list_orders(
        db,
        page=page,
        page_size=page_size,
        q=q,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
        sort=sort,
        direction=direction,
    )
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def create_order(data: OrderWrite, db: Session = Depends(get_db)) -> OrderOut:
    return order_service.to_order_out(order_service.create_order(db, data))


@router.get("/{order_id}/receipt", response_model=OrderOut)
def order_receipt(order_id: uuid.UUID, db: Session = Depends(get_db)) -> OrderOut:
    return order_service.to_order_out(order_service.get_order(db, order_id))


@router.get("/{order_id}", response_model=OrderOut)
def get_order(order_id: uuid.UUID, db: Session = Depends(get_db)) -> OrderOut:
    return order_service.to_order_out(order_service.get_order(db, order_id))


@router.put("/{order_id}", response_model=OrderOut)
def update_order(order_id: uuid.UUID, data: OrderWrite, db: Session = Depends(get_db)) -> OrderOut:
    return order_service.to_order_out(order_service.update_order(db, order_id, data))


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(order_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    order_service.delete_order(db, order_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{order_id}/items", response_model=OrderOut, status_code=status.HTTP_201_CREATED)
def add_order_item(order_id: uuid.UUID, data: OrderItemIn, db: Session = Depends(get_db)) -> OrderOut:
    return order_service.to_order_out(order_service.add_item(db, order_id, data))


@router.put("/{order_id}/items/{item_id}", response_model=OrderOut)
def update_order_item(
    order_id: uuid.UUID,
    item_id: uuid.UUID,
    data: OrderItemIn,
    db: Session = Depends(get_db),
) -> OrderOut:
    return order_service.to_order_out(order_service.update_item(db, order_id, item_id, data))


@router.delete("/{order_id}/items/{item_id}", response_model=OrderOut)
def delete_order_item(order_id: uuid.UUID, item_id: uuid.UUID, db: Session = Depends(get_db)) -> OrderOut:
    return order_service.to_order_out(order_service.delete_item(db, order_id, item_id))


@router.post("/{order_id}/confirm", response_model=OrderOut)
def confirm_order(order_id: uuid.UUID, db: Session = Depends(get_db)) -> OrderOut:
    return order_service.to_order_out(order_service.confirm_order(db, order_id))


@router.post("/{order_id}/cancel", response_model=OrderOut)
def cancel_order(order_id: uuid.UUID, db: Session = Depends(get_db)) -> OrderOut:
    return order_service.to_order_out(order_service.cancel_order(db, order_id))


@router.post("/{order_id}/complete", response_model=OrderOut)
def complete_order(order_id: uuid.UUID, db: Session = Depends(get_db)) -> OrderOut:
    return order_service.to_order_out(order_service.complete_order(db, order_id))
