import re
import uuid


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug[:160] or "item"


def retired_key(value: str, entity_id: uuid.UUID, limit: int) -> str:
    suffix = f"--{entity_id.hex[:8]}"
    trimmed = value[: max(limit - len(suffix), 1)]
    return f"{trimmed}{suffix}"
