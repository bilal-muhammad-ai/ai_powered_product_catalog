import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.attribute import AttributeOption, CategoryAttribute
from app.models.enums import AttributeScope, DataType
from app.schemas.product import AttributeValueIn


@dataclass
class PreparedValue:
    attribute: CategoryAttribute
    value_text: str | None = None
    value_numeric: Decimal | None = None
    value_boolean: bool | None = None
    value_date: date | None = None
    option_id: uuid.UUID | None = None
    option_ids: list[uuid.UUID] = field(default_factory=list)

    def canonical(self) -> str:
        data_type = self.attribute.data_type
        if data_type == DataType.text:
            return self.value_text or ""
        if data_type == DataType.number and self.value_numeric is not None:
            text = format(self.value_numeric, "f")
            if "." in text:
                text = text.rstrip("0").rstrip(".")
            return text or "0"
        if data_type == DataType.boolean:
            return "true" if self.value_boolean else "false"
        if data_type == DataType.date and self.value_date is not None:
            return self.value_date.isoformat()
        if data_type == DataType.single_select and self.option_id is not None:
            return str(self.option_id)
        return ",".join(str(option_id) for option_id in self.option_ids)


def variant_key(values: list[PreparedValue]) -> str:
    payload = "|".join(
        f"{item.attribute.id}:{item.canonical()}" for item in sorted(values, key=lambda item: str(item.attribute.id))
    )
    return hashlib.sha256(payload.encode()).hexdigest()


class FieldErrors:
    def __init__(self) -> None:
        self.items: list[dict[str, str]] = []

    def add(self, field_name: str, message: str) -> None:
        self.items.append({"field": field_name, "message": message})


def _blank(value: object, data_type: DataType) -> bool:
    if isinstance(value, bool):
        return False
    if value is None:
        return True
    if data_type == DataType.multi_select:
        return not isinstance(value, list) or len(value) == 0
    if isinstance(value, str):
        return value.strip() == ""
    return False


def _as_uuid(value: object) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        return None


def _collect_option_ids(raw_values: list[AttributeValueIn]) -> set[uuid.UUID]:
    found: set[uuid.UUID] = set()
    for item in raw_values:
        if isinstance(item.value, list):
            for entry in item.value:
                parsed = _as_uuid(entry)
                if parsed is not None:
                    found.add(parsed)
        else:
            parsed = _as_uuid(item.value)
            if parsed is not None:
                found.add(parsed)
    return found


def load_options(db: Session, option_ids: set[uuid.UUID]) -> dict[uuid.UUID, AttributeOption]:
    if not option_ids:
        return {}
    rows = db.scalars(select(AttributeOption).where(AttributeOption.id.in_(option_ids))).all()
    return {row.id: row for row in rows}


def collect_values(
    db: Session,
    attributes: list[CategoryAttribute],
    raw_values: list[AttributeValueIn],
    allowed: dict[uuid.UUID, CategoryAttribute],
    errors: FieldErrors,
    prefix: str,
    scope: AttributeScope,
) -> list[PreparedValue]:
    seen: dict[uuid.UUID, object] = {}
    for item in raw_values:
        if item.attribute_id in seen:
            errors.add(prefix, "Each attribute can only be sent once")
            continue
        seen[item.attribute_id] = item.value
        attribute = allowed.get(item.attribute_id)
        if attribute is None or attribute.scope != scope:
            errors.add(prefix, "One or more attributes do not belong to this category")

    options = load_options(db, _collect_option_ids(raw_values))
    prepared: list[PreparedValue] = []
    for attribute in attributes:
        field_name = f"{prefix}.{attribute.code}"
        if attribute.id not in seen or _blank(seen[attribute.id], attribute.data_type):
            if attribute.is_required:
                errors.add(field_name, f"{attribute.name} is required")
            continue
        value = seen[attribute.id]
        parsed = _parse_value(attribute, value, options, errors, field_name)
        if parsed is not None:
            prepared.append(parsed)
    return prepared


def _parse_value(
    attribute: CategoryAttribute,
    value: object,
    options: dict[uuid.UUID, AttributeOption],
    errors: FieldErrors,
    field_name: str,
) -> PreparedValue | None:
    data_type = attribute.data_type
    if data_type == DataType.text:
        if not isinstance(value, str):
            errors.add(field_name, f"{attribute.name} must be text")
            return None
        text = value.strip()
        if attribute.max_length is not None and len(text) > attribute.max_length:
            errors.add(field_name, f"{attribute.name} is too long")
            return None
        return PreparedValue(attribute=attribute, value_text=text)
    if data_type == DataType.number:
        if isinstance(value, bool):
            errors.add(field_name, f"{attribute.name} must be a number")
            return None
        try:
            number = Decimal(str(value))
        except (InvalidOperation, ValueError):
            errors.add(field_name, f"{attribute.name} must be a number")
            return None
        if attribute.min_value is not None and number < attribute.min_value:
            errors.add(field_name, f"{attribute.name} is below the minimum")
            return None
        if attribute.max_value is not None and number > attribute.max_value:
            errors.add(field_name, f"{attribute.name} is above the maximum")
            return None
        return PreparedValue(attribute=attribute, value_numeric=number)
    if data_type == DataType.boolean:
        if not isinstance(value, bool):
            errors.add(field_name, f"{attribute.name} must be true or false")
            return None
        return PreparedValue(attribute=attribute, value_boolean=value)
    if data_type == DataType.date:
        parsed_date = _parse_date(value)
        if parsed_date is None:
            errors.add(field_name, f"{attribute.name} must be a date")
            return None
        return PreparedValue(attribute=attribute, value_date=parsed_date)
    if data_type == DataType.single_select:
        option = _match_option(attribute, value, options, errors, field_name)
        if option is None:
            return None
        return PreparedValue(attribute=attribute, option_id=option.id)
    if data_type == DataType.multi_select:
        if attribute.scope != AttributeScope.product:
            errors.add(field_name, "Variant attributes cannot be multi-select")
            return None
        if not isinstance(value, list):
            errors.add(field_name, f"{attribute.name} must be a list of options")
            return None
        option_ids: list[uuid.UUID] = []
        for entry in value:
            option = _match_option(attribute, entry, options, errors, field_name)
            if option is None:
                return None
            if option.id not in option_ids:
                option_ids.append(option.id)
        if not option_ids:
            errors.add(field_name, f"{attribute.name} needs at least one option")
            return None
        return PreparedValue(attribute=attribute, option_ids=option_ids)
    errors.add(field_name, f"{attribute.name} has an unsupported type")
    return None


def _match_option(
    attribute: CategoryAttribute,
    value: object,
    options: dict[uuid.UUID, AttributeOption],
    errors: FieldErrors,
    field_name: str,
) -> AttributeOption | None:
    option_id = _as_uuid(value)
    option = options.get(option_id) if option_id else None
    if option is None or option.attribute_id != attribute.id:
        errors.add(field_name, f"{attribute.name} has an unknown option")
        return None
    if not option.is_active:
        errors.add(field_name, f"{attribute.name} uses an inactive option")
        return None
    return option


def _parse_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None
