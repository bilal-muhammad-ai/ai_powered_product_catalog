import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.enums import InventoryTransactionStatus, InventoryTransactionType, StockStatus
from app.schemas.common import Page
from app.schemas.inventory import (
    BalanceItem,
    CatalogHit,
    InventoryDetail,
    InventorySummary,
    MovementOut,
    MovementWrite,
    StockSettingsIn,
    StockSettingsOut,
    TransactionListItem,
    TransactionOut,
    TransactionUpdate,
    TransactionWrite,
)
from app.services import inventory as inventory_service
from app.services import inventory_reports as report_service
from app.services import inventory_transactions as transaction_service

router = APIRouter(prefix="/inventory", tags=["inventory"])


def _csv(filename: str, header: list[str], rows: list[list[object]]) -> Response:
    return Response(
        content=report_service.render_csv(header, rows),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/summary", response_model=InventorySummary)
def inventory_summary(db: Session = Depends(get_db)) -> InventorySummary:
    return inventory_service.summary(db)


@router.get("/catalog", response_model=list[CatalogHit])
def catalog(q: str | None = None, db: Session = Depends(get_db)) -> list[CatalogHit]:
    return inventory_service.search_catalog(db, q)


@router.get("/transactions", response_model=Page[TransactionListItem])
def list_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    transaction_type: InventoryTransactionType | None = None,
    status_filter: InventoryTransactionStatus | None = Query(default=None, alias="status"),
    date_from: date | None = None,
    date_to: date | None = None,
    product_id: uuid.UUID | None = None,
    q: str | None = None,
    db: Session = Depends(get_db),
) -> Page[TransactionListItem]:
    items, total = transaction_service.list_transactions(
        db,
        page=page,
        page_size=page_size,
        transaction_type=transaction_type,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
        product_id=product_id,
        q=q,
    )
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("/transactions", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(data: TransactionWrite, db: Session = Depends(get_db)) -> TransactionOut:
    return transaction_service.to_transaction_out(transaction_service.create_transaction(db, data))


@router.get("/transactions/{transaction_id}", response_model=TransactionOut)
def get_transaction(transaction_id: uuid.UUID, db: Session = Depends(get_db)) -> TransactionOut:
    return transaction_service.to_transaction_out(transaction_service.get_transaction(db, transaction_id))


@router.put("/transactions/{transaction_id}", response_model=TransactionOut)
def update_transaction(
    transaction_id: uuid.UUID,
    data: TransactionUpdate,
    db: Session = Depends(get_db),
) -> TransactionOut:
    return transaction_service.to_transaction_out(transaction_service.update_transaction(db, transaction_id, data))


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(transaction_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    transaction_service.delete_transaction(db, transaction_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/transactions/{transaction_id}/post", response_model=TransactionOut)
def post_transaction(transaction_id: uuid.UUID, db: Session = Depends(get_db)) -> TransactionOut:
    return transaction_service.to_transaction_out(transaction_service.post_transaction(db, transaction_id))


@router.post("/transactions/{transaction_id}/reverse", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def reverse_transaction(transaction_id: uuid.UUID, db: Session = Depends(get_db)) -> TransactionOut:
    return transaction_service.to_transaction_out(transaction_service.reverse_transaction(db, transaction_id))


@router.post("/opening-stock", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def opening_stock(data: MovementWrite, db: Session = Depends(get_db)) -> TransactionOut:
    created = transaction_service.create_transaction(
        db,
        data.as_transaction(InventoryTransactionType.opening_stock),
    )
    return transaction_service.to_transaction_out(created)


@router.post("/receipts", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def receipt(data: MovementWrite, db: Session = Depends(get_db)) -> TransactionOut:
    created = transaction_service.create_transaction(
        db,
        data.as_transaction(InventoryTransactionType.stock_receipt),
    )
    return transaction_service.to_transaction_out(created)


@router.post("/issues", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def issue(data: MovementWrite, db: Session = Depends(get_db)) -> TransactionOut:
    created = transaction_service.create_transaction(
        db,
        data.as_transaction(InventoryTransactionType.stock_issue),
    )
    return transaction_service.to_transaction_out(created)


@router.post("/adjustments", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def adjustment(data: MovementWrite, db: Session = Depends(get_db)) -> TransactionOut:
    created = transaction_service.create_transaction(
        db,
        data.as_transaction(InventoryTransactionType.stock_adjustment),
    )
    return transaction_service.to_transaction_out(created)


@router.get("/reports/summary")
def report_summary(
    q: str | None = None,
    category_id: uuid.UUID | None = None,
    status_filter: StockStatus | None = Query(default=None, alias="status"),
    export_format: str | None = Query(default=None, alias="format"),
    db: Session = Depends(get_db),
):
    header, rows = report_service.stock_summary(db, q=q, category_id=category_id, status=status_filter)
    if export_format == "csv":
        return _csv("stock-summary.csv", header, rows)
    return {"header": header, "rows": [[str(cell) for cell in row] for row in rows]}


@router.get("/reports/movements")
def report_movements(
    date_from: date | None = None,
    date_to: date | None = None,
    q: str | None = None,
    export_format: str | None = Query(default=None, alias="format"),
    db: Session = Depends(get_db),
):
    header, rows = report_service.movement_report(db, date_from=date_from, date_to=date_to, q=q)
    if export_format == "csv":
        return _csv("stock-movements.csv", header, rows)
    return {"header": header, "rows": [[str(cell) for cell in row] for row in rows]}


@router.get("/reports/valuation")
def report_valuation(
    q: str | None = None,
    export_format: str | None = Query(default=None, alias="format"),
    db: Session = Depends(get_db),
):
    header, rows = report_service.valuation_report(db, q=q)
    if export_format == "csv":
        return _csv("inventory-valuation.csv", header, rows)
    return {"header": header, "rows": [[str(cell) for cell in row] for row in rows]}


@router.get("/reports/low-stock")
def report_low_stock(
    export_format: str | None = Query(default=None, alias="format"),
    db: Session = Depends(get_db),
):
    header, rows = report_service.low_stock_report(db)
    if export_format == "csv":
        return _csv("low-stock.csv", header, rows)
    return {"header": header, "rows": [[str(cell) for cell in row] for row in rows]}


@router.get("/reports/out-of-stock")
def report_out_of_stock(
    export_format: str | None = Query(default=None, alias="format"),
    db: Session = Depends(get_db),
):
    header, rows = report_service.out_of_stock_report(db)
    if export_format == "csv":
        return _csv("out-of-stock.csv", header, rows)
    return {"header": header, "rows": [[str(cell) for cell in row] for row in rows]}


@router.get("", response_model=Page[BalanceItem])
def list_inventory(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = None,
    category_id: uuid.UUID | None = None,
    brand: str | None = None,
    status_filter: StockStatus | None = Query(default=None, alias="status"),
    sort: str = Query("name"),
    direction: str = Query("asc"),
    db: Session = Depends(get_db),
) -> Page[BalanceItem]:
    items, total = inventory_service.list_balances(
        db,
        page=page,
        page_size=page_size,
        q=q,
        category_id=category_id,
        brand_option_id=None,
        brand=brand,
        status=status_filter,
        sort=sort,
        direction=direction,
    )
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/{product_id}", response_model=InventoryDetail)
def inventory_detail(product_id: uuid.UUID, db: Session = Depends(get_db)) -> InventoryDetail:
    return inventory_service.get_balance(db, product_id)


@router.get("/{product_id}/history", response_model=list[MovementOut])
def inventory_history(
    product_id: uuid.UUID,
    transaction_type: InventoryTransactionType | None = None,
    db: Session = Depends(get_db),
) -> list[MovementOut]:
    return inventory_service.product_history(
        db,
        product_id,
        transaction_type=transaction_type.value if transaction_type else None,
    )


@router.put("/{product_id}/settings", response_model=StockSettingsOut)
def update_settings(
    product_id: uuid.UUID,
    data: StockSettingsIn,
    db: Session = Depends(get_db),
) -> StockSettingsOut:
    return inventory_service.save_settings(db, product_id, data)
