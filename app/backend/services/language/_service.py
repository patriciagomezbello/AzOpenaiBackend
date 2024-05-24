import re
from typing import List

import pycountry
from lingua import Language
from lingua import LanguageDetector
from lingua import LanguageDetectorBuilder
from services.language._interface import LanguageService
from services.language._languages import SUPPORTED_LANGUAGES
from services.logger import new_logger
from services.schemas import Facet
from services.timer import timer


logger = new_logger(__name__)


class LanguageProcessingService(LanguageService):
    """LanguageProcessingService provides language detection and translation services."""

    DEFAULT_LANGUAGE = Language.ENGLISH

    def __init__(self, abbreviations: dict[str, str]):
        self.detector: LanguageDetector = LanguageDetectorBuilder.from_languages(*SUPPORTED_LANGUAGES).build()
        self.abbreviations = abbreviations

    @timer()
    def detect(self, text: str) -> Language:
        """detect detects the language of the given text."""
        # Language detection is not reliable for short texts.
        if len(text) < 10:
            logger.debug(f"Text is too short for language detection: {text}")
            return self.DEFAULT_LANGUAGE

        lang = self.detector.detect_language_of(text)
        if lang is None:
            logger.debug(f"Failed to detect language of text: {text}")
            return self.DEFAULT_LANGUAGE

        return lang

    def get_lang_code(self, lang: Language) -> str:
        """get_lang_code returns the language code for the given language.
        If the language code is not found, the default language code is returned.
        """
        try:
            language = pycountry.languages.get(name=lang.name.lower())
            return language.alpha_2
        except AttributeError:
            logger.debug(f"Language code not found for language: {lang.name}")
            return self.get_lang_code(self.DEFAULT_LANGUAGE)

    def get_facet_languages(self, facets: List[Facet]) -> List[str]:
        """get_facet_languages returns a list of languages from the facet data."""
        languages: List[str] = []
        for facet in facets:
            languages.append(str(facet["value"]))
        return languages

    def replace_abbreviations(self, text: str) -> str:
        """replace_abbreviations replaces abbreviations in the text with their full forms."""
        lower_abbreviations = {abbrev.lower(): replacement for abbrev, replacement in self.abbreviations.items()}

        # pattern is a regex pattern to match words, potentially with hyphens or trailing punctuation
        pattern = re.compile(r"\b\w+(?:-\w+)?\b[.,!?;]?")

        def replacement(match: re.Match[str]) -> str:
            """replacement is a function to replace matched words with their full forms."""
            word = match.group(0)

            punctuation = ""
            if word[-1] in ".,!?;":
                punctuation = word[-1]
                word = word[:-1]

            if "-" in word:
                parts = word.split("-")
                replaced_parts = [lower_abbreviations.get(part.lower(), part) for part in parts]
                return "-".join(replaced_parts) + punctuation

            return lower_abbreviations.get(word.lower(), word) + punctuation

        return pattern.sub(replacement, text)
