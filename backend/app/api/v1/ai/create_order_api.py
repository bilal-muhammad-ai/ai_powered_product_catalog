from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.services.ai_services.order_agent.order_agent import OrderAgent, structure_order
from app.services.ai_services.order_agent.order_service import (
    retrieve_order_products_by_keyword,
    with_catalogue_details,
)
from app.services.ai_services.order_agent.schema import MatchedOrder

router = APIRouter(prefix="/ai", tags=["ai"])


class CreateOrderIn(BaseModel):
    text: str = Field(min_length=1)


def get_english_order_agent() -> OrderAgent:
    settings = get_settings()
    return OrderAgent(settings.groq_order_model, settings.groq_api_key)


@router.post("/create_order", response_model=MatchedOrder)
def create_order(
    body: CreateOrderIn,
    agent=Depends(get_english_order_agent),
    db: Session = Depends(get_db),
) -> MatchedOrder:
    order_structure = structure_order(body.text, agent)
    matched = retrieve_order_products_by_keyword(order_structure)
    return with_catalogue_details(db, matched)
