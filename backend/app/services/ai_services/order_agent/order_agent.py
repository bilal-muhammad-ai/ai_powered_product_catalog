from __future__ import annotations

import json
import re
from typing import Protocol

from pydantic import ValidationError

from app.core.exceptions import CatalogueError
from app.services.ai_services.order_agent.schema import StructuredOrder

_CHAT_MODELS: dict[tuple[str, str], object] = {}

_SYSTEM_PROMPT = """You turn one English order into JSON. Reply with JSON only, no markdown.

{
  "intent": "create_order",
  "items": [
    {"product_name": "product name" or null, "quantity": number or null, "unit": "bag" or "kg" or "ton" or "ft" or null}
  ]
}

Rules:
- One item per product.
- quantity is a number. Do not invent a quantity that was not said.
- unit is bag, kg, ton, or ft only when the text names a unit. bags means bag. feet means ft. Otherwise unit is null.
"""

_UNITS = {
    "bag": "bag",
    "bags": "bag",
    "kg": "kg",
    "kgs": "kg",
    "kilogram": "kg",
    "ton": "ton",
    "tons": "ton",
    "tonne": "ton",
    "ft": "ft",
    "foot": "ft",
    "feet": "ft",
}


class OrderChat(Protocol):
    def complete(self, text: str) -> str:
        """Return the model reply for one order."""


class OrderAgent:
    """Structure an order with a Groq chat model."""

    def __init__(self, model: str, api_key: str) -> None:
        if not api_key:
            raise RuntimeError("Missing required environment variable: GROQ_API_KEY")
        self._model_name = model
        self._api_key = api_key

    def complete(self, text: str) -> str:
        from groq import APIError
        from langchain_core.messages import HumanMessage, SystemMessage

        chat = _groq_chat(self._model_name, self._api_key)
        try:
            message = chat.invoke(
                [
                    SystemMessage(content=_SYSTEM_PROMPT),
                    HumanMessage(content=text),
                ]
            )
        except APIError as exc:
            raise CatalogueError("The order agent could not complete the request", 502) from exc
        content = _message_text(message.content)
        if not content.strip():
            raise CatalogueError("The order agent returned an empty reply", 502)
        return content


def _groq_chat(model_name: str, api_key: str):
    cached = _CHAT_MODELS.get((model_name, api_key))
    if cached is not None:
        return cached
    from langchain_groq import ChatGroq

    chat = ChatGroq(
        model=model_name,
        api_key=api_key,
        temperature=0,
        max_tokens=1024,
        reasoning_effort="low",
        reasoning_format="hidden",
    )
    _CHAT_MODELS[(model_name, api_key)] = chat
    return chat


def _message_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return str(content)
    parts: list[str] = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict):
            parts.append(str(block.get("text") or block.get("content") or ""))
    return "".join(parts)


def structure_order(text: str, chat: OrderChat) -> StructuredOrder:
    """Parse one order into items. Missing fields stay null."""
    cleaned = text.strip()
    if not cleaned:
        return StructuredOrder(items=[])
    return parse_structure(chat.complete(cleaned))


def parse_structure(raw: str) -> StructuredOrder:
    try:
        payload = json.loads(_json_object(raw))
        order = StructuredOrder.model_validate(payload)
    except CatalogueError:
        raise
    except (json.JSONDecodeError, ValidationError) as exc:
        raise CatalogueError("The order agent did not return a valid order", 502) from exc
    items = [item.model_copy(update={"unit": _normalize_unit(item.unit)}) for item in order.items]
    return StructuredOrder(items=items)


def _normalize_unit(unit: str | None) -> str | None:
    if unit is None:
        return None
    mapped = _UNITS.get(unit.strip().lower())
    return mapped or unit.strip()


def _json_object(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end <= start:
        raise CatalogueError("The order agent did not return JSON", 502)
    return text[start : end + 1]
