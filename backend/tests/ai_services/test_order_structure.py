import json

from fastapi.testclient import TestClient

from app.api.v1.ai.order_structure import get_english_order_agent
from app.core.exceptions import CatalogueError
from app.main import app
from app.services.ai_services.order_agent.order_agent import parse_structure, structure_order


class FakeChat:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.seen: str | None = None

    def complete(self, text: str) -> str:
        self.seen = text
        return self.reply


def _reply(payload: dict) -> str:
    return "```json\n" + json.dumps(payload) + "\n```"


def test_english_order_becomes_two_items():
    chat = FakeChat(
        _reply(
            {
                "intent": "create_order",
                "items": [
                    {"product_name": "Lucky Cement", "quantity": 10, "unit": "bags"},
                    {"product_name": "Bajri", "quantity": 30, "unit": "feet"},
                ],
            }
        )
    )

    order = structure_order("10 bags of Lucky Cement and 30 feet of bajri", chat)

    assert order.intent == "create_order"
    assert [(item.product_name, item.quantity, item.unit) for item in order.items] == [
        ("Lucky Cement", 10, "bag"),
        ("Bajri", 30, "ft"),
    ]
    assert chat.seen == "10 bags of Lucky Cement and 30 feet of bajri"


def test_invalid_reply_is_rejected():
    try:
        parse_structure("this is not an order")
    except CatalogueError as exc:
        assert exc.status_code == 502
    else:
        raise AssertionError("expected a 502")


def test_order_structure_route_returns_items():
    chat = FakeChat(
        _reply(
            {
                "intent": "create_order",
                "items": [
                    {"product_name": "Lucky Cement", "quantity": 10, "unit": "bag"},
                    {"product_name": "Bajri", "quantity": 30, "unit": "ft"},
                ],
            }
        )
    )
    app.dependency_overrides[get_english_order_agent] = lambda: chat
    try:
        response = TestClient(app).post(
            "/api/v1/ai/order_structure",
            json={"text": "10 bags of Lucky Cement and 30 feet of bajri"},
        )
    finally:
        app.dependency_overrides.pop(get_english_order_agent, None)

    assert response.status_code == 200, response.text
    assert response.json() == {
        "intent": "create_order",
        "items": [
            {"product_name": "Lucky Cement", "quantity": 10, "unit": "bag"},
            {"product_name": "Bajri", "quantity": 30, "unit": "ft"},
        ],
    }
