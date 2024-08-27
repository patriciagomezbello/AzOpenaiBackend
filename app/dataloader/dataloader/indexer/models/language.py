from typing import get_args
from typing import Literal

SupportedLanguages = Literal[
    "en",
    "de",
    "hu",
    "sk",
    "ru",
    "es",
]

SUPPORTED_LANGUAGES: tuple[SupportedLanguages, ...] = get_args(SupportedLanguages)

# TODO: switch back to using `lingua` library after https://github.com/pemistahl/lingua-py/issues/199 is resolved
# from lingua import Language
# SUPPORTED_LANGUAGES: tuple[Language, ...] = (
#     Language.ENGLISH,
#     Language.GERMAN,
#     Language.HUNGARIAN,
#     Language.SLOVAK,
#     Language.RUSSIAN,
#     Language.SPANISH,
# )
