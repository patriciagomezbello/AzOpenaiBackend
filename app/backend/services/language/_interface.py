from abc import ABC
from abc import abstractmethod
from typing import List

from lingua import Language
from services.schemas import Facet


__all__ = ["LanguageService"]


class LanguageService(ABC):
    """LanguageService provides an interface for interacting with the language service."""

    @abstractmethod
    def detect(self, text: str) -> Language:
        """detect detects the language of the given text."""
        ...

    @abstractmethod
    def replace_abbreviations(self, text: str) -> str:
        """replace_abbreviations replaces abbreviations in the text with their full forms."""
        ...

    @abstractmethod
    def get_lang_code(self, lang: Language) -> str:
        """get_lang_code returns the language code for the given language."""
        ...

    @abstractmethod
    def get_facet_languages(self, facets: List[Facet]) -> List[str]:
        """get_facet_languages returns a list of languages from the facet data."""
        ...
