from dataclasses import dataclass
from typing import List


@dataclass
class CategoryResponse:
    """CategoryResponse represents the category response data."""

    # TODO: remove the Union type with v2 and use List[Category] only
    categories: List[str]
