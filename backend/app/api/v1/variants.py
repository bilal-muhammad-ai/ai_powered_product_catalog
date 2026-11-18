import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.product import VariantDetail, VariantPatch
from app.services import variants as variant_service

router = APIRouter(prefix="/variants", tags=["variants"])


@router.patch("/{variant_id}", response_model=VariantDetail)
def patch_variant(variant_id: uuid.UUID, data: VariantPatch, db: Session = Depends(get_db)) -> VariantDetail:
    variant = variant_service.get_variant(db, variant_id)
    return variant_service.patch_variant(db, variant, data)
