import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.attribute import (
    AttributeCreate,
    AttributeOptionCreate,
    AttributeOptionOut,
    AttributeOptionUpdate,
    AttributeOut,
    AttributeUpdate,
)
from app.services import attribute_schema as attribute_service

router = APIRouter(tags=["attributes"])


@router.get("/categories/{category_id}/attributes", response_model=list[AttributeOut])
def list_attributes(
    category_id: uuid.UUID,
    include_inherited: bool = True,
    active_only: bool = False,
    db: Session = Depends(get_db),
) -> list[AttributeOut]:
    return attribute_service.list_effective(
        db,
        category_id,
        include_inherited=include_inherited,
        active_only=active_only,
    )


@router.post("/categories/{category_id}/attributes", response_model=AttributeOut, status_code=status.HTTP_201_CREATED)
def create_attribute(
    category_id: uuid.UUID,
    data: AttributeCreate,
    db: Session = Depends(get_db),
) -> AttributeOut:
    attribute = attribute_service.create_attribute(db, category_id, data)
    return attribute_service.to_attribute_out(attribute, inherited=False, active_only=False)


@router.patch("/attributes/{attribute_id}", response_model=AttributeOut)
def update_attribute(
    attribute_id: uuid.UUID,
    data: AttributeUpdate,
    db: Session = Depends(get_db),
) -> AttributeOut:
    attribute = attribute_service.get_attribute(db, attribute_id)
    updated = attribute_service.update_attribute(db, attribute, data)
    return attribute_service.to_attribute_out(updated, inherited=False, active_only=False)


@router.delete("/attributes/{attribute_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attribute(attribute_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    attribute_service.delete_attribute(db, attribute_service.get_attribute(db, attribute_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/attributes/{attribute_id}/options",
    response_model=AttributeOptionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_option(
    attribute_id: uuid.UUID,
    data: AttributeOptionCreate,
    db: Session = Depends(get_db),
) -> AttributeOptionOut:
    attribute = attribute_service.get_attribute(db, attribute_id)
    return AttributeOptionOut.model_validate(attribute_service.create_option(db, attribute, data))


@router.patch("/attribute-options/{option_id}", response_model=AttributeOptionOut)
def update_option(
    option_id: uuid.UUID,
    data: AttributeOptionUpdate,
    db: Session = Depends(get_db),
) -> AttributeOptionOut:
    option = attribute_service.get_option(db, option_id)
    return AttributeOptionOut.model_validate(attribute_service.update_option(db, option, data))


@router.delete("/attribute-options/{option_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_option(option_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    attribute_service.delete_option(db, attribute_service.get_option(db, option_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
