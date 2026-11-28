"""Construction catalogue records: units, categories, attributes, and sample products.

Manufacturers are not a separate table. Cement brands are options on the Cement
brand attribute. Prices are illustrative retail figures in PKR for local testing.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.models.enums import DataType, ProductStatus, UnitType

AttributeValue = str | Decimal


@dataclass(frozen=True)
class UnitSeed:
    name: str
    symbol: str
    unit_type: UnitType


@dataclass(frozen=True)
class OptionSeed:
    label: str
    value: str


@dataclass(frozen=True)
class AttributeSeed:
    name: str
    code: str
    data_type: DataType
    sort_order: int
    options: tuple[OptionSeed, ...] = ()
    unit_symbol: str | None = None
    is_required: bool = True
    is_filterable: bool = True
    help_text: str | None = None
    min_value: Decimal | None = None
    max_value: Decimal | None = None


@dataclass(frozen=True)
class CategorySeed:
    name: str
    slug: str
    description: str
    sort_order: int
    attributes: tuple[AttributeSeed, ...]


@dataclass(frozen=True)
class VariantSeed:
    sku: str
    name: str
    selling_unit: str
    selling_price: Decimal
    attributes: dict[str, AttributeValue]
    net_quantity: Decimal | None = None
    net_quantity_unit: str | None = None
    sort_order: int = 0


@dataclass(frozen=True)
class ProductSeed:
    code: str
    sku: str
    name: str
    category_slug: str
    description: str
    base_unit: str
    selling_unit: str
    selling_price: Decimal
    attributes: dict[str, AttributeValue]
    net_quantity: Decimal | None = None
    net_quantity_unit: str | None = None
    status: ProductStatus = ProductStatus.active


def _opts(*pairs: tuple[str, str]) -> tuple[OptionSeed, ...]:
    return tuple(OptionSeed(label, value) for label, value in pairs)


def _select(
    name: str,
    code: str,
    options: tuple[OptionSeed, ...],
    sort_order: int,
    *,
    unit_symbol: str | None = None,
    required: bool = True,
    help_text: str | None = None,
) -> AttributeSeed:
    return AttributeSeed(
        name=name,
        code=code,
        data_type=DataType.single_select,
        sort_order=sort_order,
        options=options,
        unit_symbol=unit_symbol,
        is_required=required,
        help_text=help_text,
    )


def _number(
    name: str,
    code: str,
    unit_symbol: str,
    sort_order: int,
    *,
    min_value: str,
    max_value: str,
    help_text: str | None = None,
) -> AttributeSeed:
    return AttributeSeed(
        name=name,
        code=code,
        data_type=DataType.number,
        sort_order=sort_order,
        unit_symbol=unit_symbol,
        min_value=Decimal(min_value),
        max_value=Decimal(max_value),
        help_text=help_text,
    )


def _variant(
    sku: str,
    name: str,
    selling_unit: str,
    price: str,
    attributes: dict[str, AttributeValue],
    *,
    qty: str | None = None,
    qty_unit: str | None = None,
    sort_order: int = 0,
) -> VariantSeed:
    return VariantSeed(
        sku=sku,
        name=name,
        selling_unit=selling_unit,
        selling_price=Decimal(price),
        attributes=dict(attributes),
        net_quantity=Decimal(qty) if qty is not None else None,
        net_quantity_unit=qty_unit,
        sort_order=sort_order,
    )


def _product(
    _family_code: str,
    name: str,
    category_slug: str,
    description: str,
    base_unit: str,
    attributes: dict[str, AttributeValue],
    variants: tuple[VariantSeed, ...],
) -> tuple[ProductSeed, ...]:
    """Turn each former variant into its own product. Code and SKU are the variant SKU."""
    rows: list[ProductSeed] = []
    for variant in variants:
        merged = dict(attributes)
        merged.update(variant.attributes)
        rows.append(
            ProductSeed(
                code=variant.sku,
                sku=variant.sku,
                name=f"{name} — {variant.name}",
                category_slug=category_slug,
                description=description,
                base_unit=base_unit,
                selling_unit=variant.selling_unit,
                selling_price=variant.selling_price,
                attributes=merged,
                net_quantity=variant.net_quantity,
                net_quantity_unit=variant.net_quantity_unit,
            )
        )
    return tuple(rows)


UNITS: tuple[UnitSeed, ...] = (
    UnitSeed("Kilogram", "kg", UnitType.weight),
    UnitSeed("Gram", "g", UnitType.weight),
    UnitSeed("Ton", "ton", UnitType.weight),
    UnitSeed("Bag", "bag", UnitType.packaging),
    UnitSeed("Piece", "pc", UnitType.count),
    UnitSeed("Meter", "m", UnitType.length),
    UnitSeed("Feet", "ft", UnitType.length),
    UnitSeed("Inch", "in", UnitType.length),
    UnitSeed("Cubic feet", "cft", UnitType.volume),
    UnitSeed("Cubic meter", "m3", UnitType.volume),
    UnitSeed("Liter", "L", UnitType.volume),
    UnitSeed("Dozen", "doz", UnitType.count),
)

CEMENT_BRANDS: tuple[OptionSeed, ...] = _opts(
    ("Maple Leaf Cement", "maple-leaf"),
    ("Lucky Cement", "lucky"),
    ("DG Khan Cement", "dg-khan"),
    ("Fauji Cement", "fauji"),
)

_CEMENT_TYPES = _opts(
    ("OPC", "opc"),
    ("PPC", "ppc"),
    ("SRC", "src"),
    ("White cement", "white"),
)
_CEMENT_GRADES = _opts(("43 Grade", "43"), ("53 Grade", "53"))
_PACKAGING = _opts(
    ("Paper bag", "paper-bag"),
    ("Laminated PP bag", "pp-bag"),
    ("Bulk", "bulk"),
)
_BAG_WEIGHTS = _opts(("20 kg", "20"), ("50 kg", "50"))

_SAND_TYPES = _opts(
    ("River sand", "river"),
    ("Pit sand", "pit"),
    ("Manufactured sand", "manufactured"),
    ("Desert sand", "desert"),
)
_GRAIN_SIZES = _opts(("Fine", "fine"), ("Medium", "medium"), ("Coarse", "coarse"))
_SAND_SOURCES = _opts(
    ("Ravi", "ravi"),
    ("Chenab", "chenab"),
    ("Lawrencepur", "lawrencepur"),
    ("Local quarry", "quarry"),
)

_STONE_SIZES = _opts(
    ("3/8 in", "0.375"),
    ("1/2 in", "0.5"),
    ("3/4 in", "0.75"),
    ("1 in", "1"),
)
_STONE_MATERIALS = _opts(
    ("Limestone", "limestone"),
    ("Granite", "granite"),
    ("River stone", "river-stone"),
)
_STONE_GRADES = _opts(("Grade A (washed)", "a"), ("Grade B (unscreened)", "b"))

_STEEL_TYPES = _opts(
    ("Deformed bar", "deformed-bar"),
    ("Mild steel round", "mild-round"),
    ("Binding wire", "binding-wire"),
    ("Angle iron", "angle"),
)
_STEEL_GRADES = _opts(("Grade 40", "40"), ("Grade 60", "60"), ("Grade 75", "75"))

_PIPE_MATERIALS = _opts(
    ("PVC", "pvc"),
    ("CPVC", "cpvc"),
    ("PPR", "ppr"),
    ("UPVC", "upvc"),
    ("GI", "gi"),
)
_PRESSURE_RATINGS = _opts(
    ("Class B (6 bar)", "class-b"),
    ("Class C (9 bar)", "class-c"),
    ("Class D (12 bar)", "class-d"),
    ("PN 16", "pn16"),
    ("PN 20", "pn20"),
)
_PIPE_TYPES = _opts(
    ("Pressure", "pressure"),
    ("Soil", "soil"),
    ("Waste", "waste"),
    ("Drainage", "drainage"),
)

_FITTING_MATERIALS = _opts(
    ("PVC", "pvc"),
    ("CPVC", "cpvc"),
    ("PPR", "ppr"),
    ("GI", "gi"),
    ("Brass", "brass"),
)
_FITTING_TYPES = _opts(
    ("90° elbow", "elbow-90"),
    ("45° elbow", "elbow-45"),
    ("Tee", "tee"),
    ("Socket", "socket"),
    ("Reducer", "reducer"),
    ("Union", "union"),
)
_CONNECTIONS = _opts(("Solvent weld", "solvent"), ("Threaded", "threaded"))
_FITTING_DIAMETERS = _opts(
    ("1/2 in", "0.5"),
    ("3/4 in", "0.75"),
    ("1 in", "1"),
    ("1-1/2 in", "1.5"),
    ("2 in", "2"),
    ("3 in", "3"),
    ("4 in", "4"),
)

_BRUSH_TYPES = _opts(
    ("Paint", "paint"),
    ("Wire", "wire"),
    ("Whitewash", "whitewash"),
    ("Broom", "broom"),
)
_BRISTLES = _opts(
    ("Nylon", "nylon"),
    ("Natural hair", "natural-hair"),
    ("Steel wire", "steel-wire"),
    ("Polypropylene", "polypropylene"),
)
_BRUSH_HANDLES = _opts(("Wood", "wood"), ("Plastic", "plastic"), ("Steel", "steel"))

_TOOL_TYPES = _opts(
    ("Trowel", "trowel"),
    ("Hammer", "hammer"),
    ("Spirit level", "spirit-level"),
    ("Measuring tape", "measuring-tape"),
    ("Shovel", "shovel"),
    ("Pickaxe", "pickaxe"),
)
_TOOL_MATERIALS = _opts(
    ("Carbon steel", "carbon-steel"),
    ("Stainless steel", "stainless-steel"),
    ("Aluminium", "aluminium"),
    ("Wood", "wood"),
)
_TOOL_HANDLES = _opts(
    ("Wood", "wood"),
    ("Fiberglass", "fiberglass"),
    ("Steel", "steel"),
    ("Plastic", "plastic"),
)
_TOOL_SIZES = _opts(("Small", "small"), ("Medium", "medium"), ("Large", "large"))

CATEGORIES: tuple[CategorySeed, ...] = (
    CategorySeed(
        name="Cement",
        slug="cement",
        description="Portland and specialty cements sold by the bag.",
        sort_order=1,
        attributes=(
            _select("Brand", "brand", CEMENT_BRANDS, 1),
            _select("Cement Type", "cement_type", _CEMENT_TYPES, 2),
            _select("Grade", "grade", _CEMENT_GRADES, 3),
            _select("Packaging", "packaging", _PACKAGING, 4),
            _select(
                "Bag Weight",
                "bag_weight",
                _BAG_WEIGHTS,
                5,
                unit_symbol="kg",
                help_text="Filled weight of one bag.",
            ),
        ),
    ),
    CategorySeed(
        name="Sand",
        slug="sand",
        description="Fine aggregate for mortar, plaster, and concrete.",
        sort_order=2,
        attributes=(
            _select("Sand Type", "sand_type", _SAND_TYPES, 1),
            _select("Grain Size", "grain_size", _GRAIN_SIZES, 2),
            _select("Source", "source", _SAND_SOURCES, 3),
        ),
    ),
    CategorySeed(
        name="Gravel / Crush",
        slug="gravel-crush",
        description="Crushed stone and gravel for concrete and road base.",
        sort_order=3,
        attributes=(
            _select("Stone Size", "stone_size", _STONE_SIZES, 1),
            _select("Material Type", "material_type", _STONE_MATERIALS, 2),
            _select("Grade", "grade", _STONE_GRADES, 3),
        ),
    ),
    CategorySeed(
        name="Steel & Iron",
        slug="steel-iron",
        description="Reinforcement bars and mild steel rounds.",
        sort_order=4,
        attributes=(
            _select("Steel Type", "steel_type", _STEEL_TYPES, 1),
            _number(
                "Diameter",
                "diameter",
                "in",
                2,
                min_value="0.25",
                max_value="2",
                help_text="Nominal diameter in inches. 1/2 in is about 12 mm.",
            ),
            _number(
                "Length",
                "length",
                "ft",
                3,
                min_value="1",
                max_value="60",
                help_text="Cut length in feet. Deformed bars are commonly 40 ft.",
            ),
            _select("Grade", "grade", _STEEL_GRADES, 4),
        ),
    ),
    CategorySeed(
        name="Sanitary Pipes",
        slug="sanitary-pipes",
        description="Pressure, soil, waste, and drainage pipes.",
        sort_order=5,
        attributes=(
            _select("Material", "material", _PIPE_MATERIALS, 1),
            _number(
                "Diameter",
                "diameter",
                "in",
                2,
                min_value="0.5",
                max_value="12",
                help_text="Nominal bore in inches.",
            ),
            _number(
                "Length",
                "length",
                "m",
                3,
                min_value="1",
                max_value="6",
                help_text="Pipe length in metres.",
            ),
            _select("Pressure Rating", "pressure_rating", _PRESSURE_RATINGS, 4),
            _select("Pipe Type", "pipe_type", _PIPE_TYPES, 5),
        ),
    ),
    CategorySeed(
        name="Pipe Fittings",
        slug="pipe-fittings",
        description="Elbows, tees, sockets, and other pipe fittings.",
        sort_order=6,
        attributes=(
            _select("Material", "material", _FITTING_MATERIALS, 1),
            _select("Fitting Type", "fitting_type", _FITTING_TYPES, 2),
            _select("Diameter", "diameter", _FITTING_DIAMETERS, 3),
            _select("Connection", "connection", _CONNECTIONS, 4),
        ),
    ),
    CategorySeed(
        name="Brushes",
        slug="brushes",
        description="Paint, wire, and whitewash brushes.",
        sort_order=7,
        attributes=(
            _select("Brush Type", "brush_type", _BRUSH_TYPES, 1),
            _number(
                "Width",
                "width",
                "in",
                2,
                min_value="0.5",
                max_value="24",
                help_text="Brush width in inches.",
            ),
            _select("Bristle Material", "bristle_material", _BRISTLES, 3),
            _select("Handle Material", "handle_material", _BRUSH_HANDLES, 4),
        ),
    ),
    CategorySeed(
        name="Construction Tools",
        slug="construction-tools",
        description="Hand tools for masonry and site work.",
        sort_order=8,
        attributes=(
            _select("Tool Type", "tool_type", _TOOL_TYPES, 1),
            _select("Material", "material", _TOOL_MATERIALS, 2),
            _select("Size", "size", _TOOL_SIZES, 3),
            _select("Handle Material", "handle_material", _TOOL_HANDLES, 4),
        ),
    ),
)

_PRODUCT_GROUPS: tuple[tuple[ProductSeed, ...], ...] = (
    _product(
        "CEM-ML-OPC43",
        "Maple Leaf Cement OPC 43",
        "cement",
        "Ordinary Portland cement, 43 grade, for general concrete and mortar.",
        "kg",
        {"brand": "maple-leaf", "cement_type": "opc", "grade": "43", "packaging": "paper-bag"},
        (
            _variant(
                "CEM-ML-OPC43-20",
                "20 kg bag",
                "bag",
                "640.00",
                {"bag_weight": "20"},
                qty="20",
                qty_unit="kg",
                sort_order=1,
            ),
            _variant(
                "CEM-ML-OPC43-50",
                "50 kg bag",
                "bag",
                "1480.00",
                {"bag_weight": "50"},
                qty="50",
                qty_unit="kg",
                sort_order=2,
            ),
        ),
    ),
    _product(
        "CEM-LC-OPC53",
        "Lucky Cement OPC 53",
        "cement",
        "Ordinary Portland cement, 53 grade, for higher early strength.",
        "kg",
        {"brand": "lucky", "cement_type": "opc", "grade": "53", "packaging": "paper-bag"},
        (
            _variant(
                "CEM-LC-OPC53-20",
                "20 kg bag",
                "bag",
                "680.00",
                {"bag_weight": "20"},
                qty="20",
                qty_unit="kg",
                sort_order=1,
            ),
            _variant(
                "CEM-LC-OPC53-50",
                "50 kg bag",
                "bag",
                "1580.00",
                {"bag_weight": "50"},
                qty="50",
                qty_unit="kg",
                sort_order=2,
            ),
        ),
    ),
    _product(
        "CEM-DG-PPC43",
        "DG Khan Cement PPC 43",
        "cement",
        "Portland pozzolana cement for plaster, masonry, and mass concrete.",
        "kg",
        {"brand": "dg-khan", "cement_type": "ppc", "grade": "43", "packaging": "paper-bag"},
        (
            _variant(
                "CEM-DG-PPC43-50",
                "50 kg bag",
                "bag",
                "1420.00",
                {"bag_weight": "50"},
                qty="50",
                qty_unit="kg",
            ),
        ),
    ),
    _product(
        "CEM-FJ-SRC43",
        "Fauji Cement SRC 43",
        "cement",
        "Sulphate-resistant cement for foundations and sulphate-bearing soil.",
        "kg",
        {"brand": "fauji", "cement_type": "src", "grade": "43", "packaging": "pp-bag"},
        (
            _variant(
                "CEM-FJ-SRC43-50",
                "50 kg laminated bag",
                "bag",
                "1680.00",
                {"bag_weight": "50"},
                qty="50",
                qty_unit="kg",
            ),
        ),
    ),
    _product(
        "SND-RAVI",
        "Ravi River Sand",
        "sand",
        "Washed river sand from the Ravi, sold loose by the cubic foot.",
        "cft",
        {"sand_type": "river", "source": "ravi"},
        (
            _variant(
                "SND-RAVI-FINE",
                "Fine",
                "cft",
                "80.00",
                {"grain_size": "fine"},
                qty="1",
                qty_unit="cft",
                sort_order=1,
            ),
            _variant(
                "SND-RAVI-MED",
                "Medium",
                "cft",
                "75.00",
                {"grain_size": "medium"},
                qty="1",
                qty_unit="cft",
                sort_order=2,
            ),
            _variant(
                "SND-RAVI-CRS",
                "Coarse",
                "cft",
                "70.00",
                {"grain_size": "coarse"},
                qty="1",
                qty_unit="cft",
                sort_order=3,
            ),
        ),
    ),
    _product(
        "SND-CHENAB",
        "Chenab Pit Sand",
        "sand",
        "Pit sand from the Chenab belt, sold by the cubic metre.",
        "m3",
        {"sand_type": "pit", "source": "chenab"},
        (
            _variant(
                "SND-CHENAB-MED",
                "Medium",
                "m3",
                "4500.00",
                {"grain_size": "medium"},
                qty="1",
                qty_unit="m3",
                sort_order=1,
            ),
            _variant(
                "SND-CHENAB-CRS",
                "Coarse",
                "m3",
                "4200.00",
                {"grain_size": "coarse"},
                qty="1",
                qty_unit="m3",
                sort_order=2,
            ),
        ),
    ),
    _product(
        "GRV-MARGALLA",
        "Margalla Limestone Crush",
        "gravel-crush",
        "Washed Margalla limestone crush for structural concrete.",
        "cft",
        {"material_type": "limestone", "grade": "a"},
        (
            _variant(
                "GRV-MARGALLA-12",
                "1/2 in",
                "cft",
                "100.00",
                {"stone_size": "0.5"},
                qty="1",
                qty_unit="cft",
                sort_order=1,
            ),
            _variant(
                "GRV-MARGALLA-34",
                "3/4 in",
                "cft",
                "95.00",
                {"stone_size": "0.75"},
                qty="1",
                qty_unit="cft",
                sort_order=2,
            ),
        ),
    ),
    _product(
        "GRV-SARGODHA",
        "Sargodha Granite Crush",
        "gravel-crush",
        "Unscreened Sargodha granite crush, sold by the ton.",
        "ton",
        {"material_type": "granite", "grade": "b"},
        (
            _variant(
                "GRV-SARGODHA-34",
                "3/4 in",
                "ton",
                "3600.00",
                {"stone_size": "0.75"},
                qty="1",
                qty_unit="ton",
                sort_order=1,
            ),
            _variant(
                "GRV-SARGODHA-1",
                "1 in",
                "ton",
                "3500.00",
                {"stone_size": "1"},
                qty="1",
                qty_unit="ton",
                sort_order=2,
            ),
        ),
    ),
    _product(
        "STL-TMT-60",
        "Grade 60 Deformed Bar",
        "steel-iron",
        "Hot-rolled deformed reinforcement bar, 40 ft lengths.",
        "pc",
        {"steel_type": "deformed-bar", "grade": "60"},
        (
            _variant(
                "STL-TMT-60-050-40",
                "1/2 in x 40 ft",
                "pc",
                "3100.00",
                {"diameter": Decimal("0.5"), "length": Decimal("40")},
                qty="40",
                qty_unit="ft",
                sort_order=1,
            ),
            _variant(
                "STL-TMT-60-062-40",
                "5/8 in x 40 ft",
                "pc",
                "5300.00",
                {"diameter": Decimal("0.625"), "length": Decimal("40")},
                qty="40",
                qty_unit="ft",
                sort_order=2,
            ),
            _variant(
                "STL-TMT-60-075-40",
                "3/4 in x 40 ft",
                "pc",
                "8200.00",
                {"diameter": Decimal("0.75"), "length": Decimal("40")},
                qty="40",
                qty_unit="ft",
                sort_order=3,
            ),
        ),
    ),
    _product(
        "STL-MS-40",
        "Grade 40 Mild Steel Round",
        "steel-iron",
        "Plain mild steel round bar in 20 ft lengths.",
        "pc",
        {"steel_type": "mild-round", "grade": "40"},
        (
            _variant(
                "STL-MS-40-037-20",
                "3/8 in x 20 ft",
                "pc",
                "1200.00",
                {"diameter": Decimal("0.375"), "length": Decimal("20")},
                qty="20",
                qty_unit="ft",
                sort_order=1,
            ),
            _variant(
                "STL-MS-40-050-20",
                "1/2 in x 20 ft",
                "pc",
                "1800.00",
                {"diameter": Decimal("0.5"), "length": Decimal("20")},
                qty="20",
                qty_unit="ft",
                sort_order=2,
            ),
        ),
    ),
    _product(
        "PIP-UPVC-SOIL",
        "UPVC Soil Pipe Class B",
        "sanitary-pipes",
        "UPVC soil pipe for above-ground waste stacks.",
        "pc",
        {"material": "upvc", "pressure_rating": "class-b", "pipe_type": "soil"},
        (
            _variant(
                "PIP-UPVC-3-3",
                "3 in x 3 m",
                "pc",
                "1200.00",
                {"diameter": Decimal("3"), "length": Decimal("3")},
                qty="3",
                qty_unit="m",
                sort_order=1,
            ),
            _variant(
                "PIP-UPVC-4-3",
                "4 in x 3 m",
                "pc",
                "1900.00",
                {"diameter": Decimal("4"), "length": Decimal("3")},
                qty="3",
                qty_unit="m",
                sort_order=2,
            ),
            _variant(
                "PIP-UPVC-4-4",
                "4 in x 4 m",
                "pc",
                "2450.00",
                {"diameter": Decimal("4"), "length": Decimal("4")},
                qty="4",
                qty_unit="m",
                sort_order=3,
            ),
        ),
    ),
    _product(
        "PIP-PPR-PN20",
        "PPR Pressure Pipe PN20",
        "sanitary-pipes",
        "PPR pipe for hot and cold water, pressure class PN 20.",
        "pc",
        {"material": "ppr", "pressure_rating": "pn20", "pipe_type": "pressure"},
        (
            _variant(
                "PIP-PPR-075-4",
                "3/4 in x 4 m",
                "pc",
                "1300.00",
                {"diameter": Decimal("0.75"), "length": Decimal("4")},
                qty="4",
                qty_unit="m",
                sort_order=1,
            ),
            _variant(
                "PIP-PPR-1-4",
                "1 in x 4 m",
                "pc",
                "1950.00",
                {"diameter": Decimal("1"), "length": Decimal("4")},
                qty="4",
                qty_unit="m",
                sort_order=2,
            ),
        ),
    ),
    _product(
        "FIT-PVC-EL90",
        "PVC 90° Elbow",
        "pipe-fittings",
        "Solvent-weld PVC elbow for pressure and waste lines.",
        "pc",
        {"material": "pvc", "fitting_type": "elbow-90", "connection": "solvent"},
        (
            _variant(
                "FIT-PVC-EL90-1",
                "1 in",
                "pc",
                "70.00",
                {"diameter": "1"},
                qty="40",
                qty_unit="g",
                sort_order=1,
            ),
            _variant(
                "FIT-PVC-EL90-2",
                "2 in",
                "pc",
                "150.00",
                {"diameter": "2"},
                qty="90",
                qty_unit="g",
                sort_order=2,
            ),
            _variant(
                "FIT-PVC-EL90-4",
                "4 in",
                "pc",
                "420.00",
                {"diameter": "4"},
                qty="220",
                qty_unit="g",
                sort_order=3,
            ),
        ),
    ),
    _product(
        "FIT-GI-TEE",
        "GI Threaded Tee",
        "pipe-fittings",
        "Galvanised malleable-iron tee with BSP threads.",
        "pc",
        {"material": "gi", "fitting_type": "tee", "connection": "threaded"},
        (
            _variant(
                "FIT-GI-TEE-050",
                "1/2 in",
                "pc",
                "190.00",
                {"diameter": "0.5"},
                qty="180",
                qty_unit="g",
                sort_order=1,
            ),
            _variant(
                "FIT-GI-TEE-075",
                "3/4 in",
                "pc",
                "250.00",
                {"diameter": "0.75"},
                qty="280",
                qty_unit="g",
                sort_order=2,
            ),
            _variant(
                "FIT-GI-TEE-1",
                "1 in",
                "pc",
                "340.00",
                {"diameter": "1"},
                qty="420",
                qty_unit="g",
                sort_order=3,
            ),
        ),
    ),
    _product(
        "BRU-PAINT",
        "Wooden Paint Brush",
        "brushes",
        "Nylon paint brush with a wooden handle.",
        "pc",
        {"brush_type": "paint", "bristle_material": "nylon", "handle_material": "wood"},
        (
            _variant(
                "BRU-PAINT-2",
                "2 in",
                "pc",
                "260.00",
                {"width": Decimal("2")},
                qty="1",
                qty_unit="pc",
                sort_order=1,
            ),
            _variant(
                "BRU-PAINT-3",
                "3 in",
                "pc",
                "340.00",
                {"width": Decimal("3")},
                qty="1",
                qty_unit="pc",
                sort_order=2,
            ),
            _variant(
                "BRU-PAINT-4",
                "4 in",
                "pc",
                "430.00",
                {"width": Decimal("4")},
                qty="1",
                qty_unit="pc",
                sort_order=3,
            ),
        ),
    ),
    _product(
        "BRU-WIRE",
        "Steel Wire Brush",
        "brushes",
        "Scratch brush with steel bristles and a steel handle.",
        "pc",
        {"brush_type": "wire", "bristle_material": "steel-wire", "handle_material": "steel"},
        (
            _variant(
                "BRU-WIRE-2",
                "2 in",
                "pc",
                "250.00",
                {"width": Decimal("2")},
                qty="1",
                qty_unit="pc",
                sort_order=1,
            ),
            _variant(
                "BRU-WIRE-4",
                "4 in",
                "pc",
                "380.00",
                {"width": Decimal("4")},
                qty="1",
                qty_unit="pc",
                sort_order=2,
            ),
        ),
    ),
    _product(
        "BRU-WHITEWASH",
        "Whitewash Brush",
        "brushes",
        "Polypropylene whitewash brush with a plastic handle, packed by the dozen.",
        "doz",
        {"brush_type": "whitewash", "bristle_material": "polypropylene", "handle_material": "plastic"},
        (
            _variant(
                "BRU-WHITEWASH-7",
                "7 in, dozen",
                "doz",
                "1400.00",
                {"width": Decimal("7")},
                qty="12",
                qty_unit="pc",
            ),
        ),
    ),
    _product(
        "TLS-TROWEL",
        "Masonry Trowel",
        "construction-tools",
        "Brick trowel with a carbon-steel blade and wooden handle.",
        "pc",
        {"tool_type": "trowel", "material": "carbon-steel", "handle_material": "wood"},
        (
            _variant(
                "TLS-TROWEL-S",
                "Small",
                "pc",
                "550.00",
                {"size": "small"},
                qty="1",
                qty_unit="pc",
                sort_order=1,
            ),
            _variant(
                "TLS-TROWEL-L",
                "Large",
                "pc",
                "750.00",
                {"size": "large"},
                qty="1",
                qty_unit="pc",
                sort_order=2,
            ),
        ),
    ),
    _product(
        "TLS-HAMMER",
        "Claw Hammer",
        "construction-tools",
        "Claw hammer with a carbon-steel head and fiberglass handle.",
        "pc",
        {"tool_type": "hammer", "material": "carbon-steel", "handle_material": "fiberglass"},
        (
            _variant(
                "TLS-HAMMER-M",
                "Medium",
                "pc",
                "1100.00",
                {"size": "medium"},
                qty="1",
                qty_unit="pc",
                sort_order=1,
            ),
            _variant(
                "TLS-HAMMER-L",
                "Large",
                "pc",
                "1450.00",
                {"size": "large"},
                qty="1",
                qty_unit="pc",
                sort_order=2,
            ),
        ),
    ),
)

PRODUCTS: tuple[ProductSeed, ...] = tuple(product for group in _PRODUCT_GROUPS for product in group)
