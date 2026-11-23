from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.services.ai_services.order_agent.order_agent import OrderAgent, structure_order
from app.services.ai_services.order_agent.schema import StructuredOrder

router = APIRouter(prefix="/ai", tags=["ai"])


class OrderStructureIn(BaseModel):
    text: str = Field(min_length=1)


def get_english_order_agent() -> OrderAgent:
    settings = get_settings()
    return OrderAgent(settings.groq_order_model, settings.groq_api_key)


@router.post("/order_structure", response_model=StructuredOrder)
def create_order_structure(body: OrderStructureIn, agent=Depends(get_english_order_agent)) -> StructuredOrder:
    return structure_order(body.text, agent)
