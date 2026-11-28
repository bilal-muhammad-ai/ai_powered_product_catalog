import threading
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.exceptions import CatalogueError
from app.models.enums import InventoryTransactionType, ProductStatus
from app.models.inventory import InventoryTransaction, InventoryTransactionItem, StockBalance
from app.models.order.item import OrderItem
from app.models.order.order import Order
from app.models.product import Product
from app.schemas.category import CategoryCreate
from app.schemas.inventory import TransactionItemIn, TransactionWrite
from app.schemas.order.order import OrderItemIn, OrderWrite
from app.schemas.product import ProductWrite
from app.schemas.unit import UnitCreate
from app.services.categories import create_category
from app.services.inventory_transactions import create_transaction
from app.services.order.orders import confirm_order, create_order
from app.services.products import save_product
from app.services.units import create_unit


def test_concurrent_order_confirms_cannot_oversell(engine):
    setup = Session(bind=engine)
    try:
        unit = create_unit(setup, UnitCreate(name="Bag", symbol=f"bag-{uuid.uuid4().hex[:8]}", unit_type="packaging"))
        category = create_category(setup, CategoryCreate(name=f"Yard {uuid.uuid4().hex[:6]}"))
        product = save_product(
            setup,
            ProductWrite(
                category_id=category.id,
                name="Concurrent order cement",
                sku=f"ORD-{uuid.uuid4().hex[:8]}",
                selling_unit_id=unit.id,
                selling_price=Decimal("12"),
                status=ProductStatus.active,
            ),
        )
        create_transaction(
            setup,
            TransactionWrite(
                transaction_type=InventoryTransactionType.opening_stock,
                transaction_date=date(2026, 11, 19),
                items=[TransactionItemIn(product_id=product.id, unit_id=unit.id, quantity=Decimal("10"), unit_cost=Decimal("10"))],
                post=True,
            ),
        )
        order_ids = []
        for _ in range(2):
            order = create_order(
                setup,
                OrderWrite(
                    order_date=date(2026, 11, 19),
                    items=[OrderItemIn(product_id=product.id, unit_id=unit.id, quantity=Decimal("8"), unit_price=Decimal("12"))],
                ),
            )
            order_ids.append(order.id)
        product_id = product.id
        setup.commit()
    except Exception:
        setup.rollback()
        raise
    finally:
        setup.close()

    errors: list[str] = []

    def worker(order_id: uuid.UUID) -> None:
        local = Session(bind=engine)
        try:
            confirm_order(local, order_id)
            local.commit()
        except CatalogueError as exc:
            local.rollback()
            errors.append(exc.message)
        finally:
            local.close()

    threads = [threading.Thread(target=worker, args=(order_id,)) for order_id in order_ids]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    check = Session(bind=engine)
    try:
        balance = check.scalar(select(StockBalance).where(StockBalance.product_id == product_id))
        assert balance is not None
        assert balance.quantity_on_hand == Decimal("2.0000")
        assert len(errors) == 1
        assert "Insufficient stock" in errors[0]
        check.execute(delete(OrderItem).where(OrderItem.product_id == product_id))
        check.execute(delete(Order).where(Order.id.in_(order_ids)))
        txn_ids = list(check.scalars(select(InventoryTransactionItem.transaction_id).where(InventoryTransactionItem.product_id == product_id)))
        check.execute(delete(InventoryTransactionItem).where(InventoryTransactionItem.product_id == product_id))
        if txn_ids:
            check.execute(delete(InventoryTransaction).where(InventoryTransaction.id.in_(txn_ids)))
        check.execute(delete(StockBalance).where(StockBalance.product_id == product_id))
        check.execute(delete(Product).where(Product.id == product_id))
        check.commit()
    finally:
        check.close()
