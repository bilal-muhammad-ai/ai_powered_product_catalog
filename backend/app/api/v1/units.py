import uuid

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.common import Page
from app.schemas.unit import UnitCreate, UnitOut, UnitUpdate
from app.services import units as unit_service

router = APIRouter(prefix="/units", tags=["units"])


@router.get("", response_model=Page[UnitOut])
def list_units(
    q: str | None = None,
    include_inactive: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> Page[UnitOut]:
    rows = unit_service.list_units(db, q=q, include_inactive=include_inactive)
    start = (page - 1) * page_size
    window = rows[start : start + page_size]
    return Page(items=[UnitOut.model_validate(row) for row in window], total=len(rows), page=page, page_size=page_size)


@router.post("", response_model=UnitOut, status_code=status.HTTP_201_CREATED)
def create_unit(data: UnitCreate, db: Session = Depends(get_db)) -> UnitOut:
    return UnitOut.model_validate(unit_service.create_unit(db, data))


@router.get("/{unit_id}", response_model=UnitOut)
def get_unit(unit_id: uuid.UUID, db: Session = Depends(get_db)) -> UnitOut:
    return UnitOut.model_validate(unit_service.get_unit(db, unit_id))


@router.patch("/{unit_id}", response_model=UnitOut)
def update_unit(unit_id: uuid.UUID, data: UnitUpdate, db: Session = Depends(get_db)) -> UnitOut:
    unit = unit_service.get_unit(db, unit_id)
    return UnitOut.model_validate(unit_service.update_unit(db, unit, data))


@router.delete("/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_unit(unit_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    unit_service.delete_unit(db, unit_service.get_unit(db, unit_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
