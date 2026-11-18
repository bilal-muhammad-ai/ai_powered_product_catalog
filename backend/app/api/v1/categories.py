import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.category import CategoryCreate, CategoryNode, CategoryOut, CategoryUpdate
from app.services import categories as category_service

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryNode])
def list_categories(db: Session = Depends(get_db)) -> list[CategoryNode]:
    return category_service.to_node_list(db)


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
def create_category(data: CategoryCreate, db: Session = Depends(get_db)) -> CategoryOut:
    return category_service.to_out(category_service.create_category(db, data))


@router.get("/{category_id}", response_model=CategoryOut)
def get_category(category_id: uuid.UUID, db: Session = Depends(get_db)) -> CategoryOut:
    return category_service.to_out(category_service.get_category(db, category_id))


@router.patch("/{category_id}", response_model=CategoryOut)
def update_category(category_id: uuid.UUID, data: CategoryUpdate, db: Session = Depends(get_db)) -> CategoryOut:
    category = category_service.get_category(db, category_id)
    return category_service.to_out(category_service.update_category(db, category, data))


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: uuid.UUID, db: Session = Depends(get_db)) -> Response:
    category_service.delete_category(db, category_service.get_category(db, category_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
