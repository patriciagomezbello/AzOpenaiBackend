from dataclasses import dataclass


@dataclass
class CategoryResponse:
    """CategoryResponse represents the category response data."""

    categories: list[str]
