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


class ProductStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    archived = "archived"


class InventoryTransactionType(str, enum.Enum):
    opening_stock = "OPENING_STOCK"
    stock_receipt = "STOCK_RECEIPT"
    stock_issue = "STOCK_ISSUE"
    stock_adjustment = "STOCK_ADJUSTMENT"
    reversal = "REVERSAL"


class InventoryTransactionStatus(str, enum.Enum):
    draft = "DRAFT"
    posted = "POSTED"
    cancelled = "CANCELLED"
    reversed = "REVERSED"


class StockStatus(str, enum.Enum):
    in_stock = "in_stock"
    low_stock = "low_stock"
    out_of_stock = "out_of_stock"
