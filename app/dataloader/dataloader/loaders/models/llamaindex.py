from dataloader.loaders.models import BaseConfig
from pydantic import model_validator


class JiraConfig(BaseConfig):
    username: str
    """The username of the user."""
    token_ref: str
    """Name of variable where API key of user is put."""
    project_key: str
    """The key of the project."""

    @model_validator(mode="before")
    def validate_url(cls, values):
        """It's needed as Llama Index JiraReader accept only format without protocol"""
        if "url" in values:
            url = values["url"]
            values["url"] = url.split("//")[-1]
        return values
