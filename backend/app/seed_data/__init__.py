"""Declarative seed content for the construction catalogue.

These records are not application behaviour. `app.seed` is the only loader.
"""

from app.seed_data.catalogue import CATEGORIES, CEMENT_BRANDS, PRODUCTS, UNITS

__all__ = ["CATEGORIES", "CEMENT_BRANDS", "PRODUCTS", "UNITS"]
