from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.v1 import attributes, categories, inventory, products, units

router = APIRouter()
router.include_router(units.router)
router.include_router(categories.router)
router.include_router(attributes.router)
router.include_router(products.router)
router.include_router(inventory.router)


@router.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
