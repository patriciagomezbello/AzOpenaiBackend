from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field


class HealthDetailedStatus(BaseModel):
    """Contains information about the application sub-systems health."""

    status_openai: bool | None = Field(None)
    """Application can connect to openai backend."""

    status_search: bool | None = Field(None)
    """Application can connect to search backend."""

    budget: int | None = Field(None)
    """Percentage 0-100 of the consumed budget."""


class HealthStatusResponse(BaseModel):
    """Contains information about the application health."""

    healthy: bool
    """Indicates if the application is healthy."""

    status: HealthDetailedStatus | None
    """Status of the applications sub-systems."""

    # Extra Pydantic Configuration to supply an example.
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"healthy": True, "status": {"status_openai": True, "status_search": True, "budget": 34}}]}
    )
