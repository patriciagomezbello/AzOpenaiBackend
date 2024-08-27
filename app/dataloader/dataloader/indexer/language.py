import pycountry
from dataloader.base import new_logger
from dataloader.indexer.models import SupportedLanguages
from lingua import Language
from lingua import LanguageDetector as LinguaLanguageDetector
from lingua import LanguageDetectorBuilder


logger = new_logger(__name__)

# TODO: This is a workaround until https://github.com/pemistahl/lingua-py/issues/199 is resolved and a new release is available.
LANGUAGE_CODE_MAP = {
    "en": Language.ENGLISH,
    "de": Language.GERMAN,
    "hu": Language.HUNGARIAN,
    "sk": Language.SLOVAK,
    "ru": Language.RUSSIAN,
    "es": Language.SPANISH,
}


class LanguageDetector:
    DEFAULT_LANGUAGE = Language.ENGLISH

    # TODO: revert the languages parameter to a list[Language] = SUPPORTED_LANGUAGES once the issue is resolved.
    def __init__(self, languages: tuple[SupportedLanguages, ...]):
        langs = [LANGUAGE_CODE_MAP[lang] for lang in languages]
        self.detector: LinguaLanguageDetector = LanguageDetectorBuilder.from_languages(*langs).build()

    def detect(self, text: str) -> Language:
        """detect detects the language of the given text."""
        # Language detection is not reliable for short texts.
        if len(text) < 10:
            logger.info(f"Text is too short for language detection: {text}")
            return self.DEFAULT_LANGUAGE

        lang = self.detector.detect_language_of(text)
        if lang is None:
            logger.info(f"Failed to detect language of text: {text}")
            return self.DEFAULT_LANGUAGE

        return lang

    def get_lang_code(self, lang: Language) -> str:
        """get_lang_code returns the language code for the given language.
        If the language code is not found, the default language code is returned.
        """
        try:
            language = pycountry.languages.get(name=lang.name.lower())
            return language.alpha_2  # type: ignore
        except AttributeError:
            logger.debug(f"Language code not found for language: {lang.name}")
            return self.get_lang_code(self.DEFAULT_LANGUAGE)
