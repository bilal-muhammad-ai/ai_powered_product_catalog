import enum


class UnitType(str, enum.Enum):
    weight = "weight"
    volume = "volume"
    length = "length"
    area = "area"
    count = "count"
    packaging = "packaging"


class DataType(str, enum.Enum):
    text = "text"
    number = "number"
    boolean = "boolean"
    date = "date"
    single_select = "single_select"
    multi_select = "multi_select"


class AttributeScope(str, enum.Enum):
    product = "product"
    variant = "variant"


class ProductStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    archived = "archived"
