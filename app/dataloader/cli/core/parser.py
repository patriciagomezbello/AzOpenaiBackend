import argparse

from pydantic import BaseModel


class ParsedArgs(BaseModel):
    webloader_config: str
    indexer_config: str
    roles_config: str
    verbose: bool


def parse_args() -> ParsedArgs:
    args = _parser.parse_args()
    return ParsedArgs(
        webloader_config=args.webloader_config,
        indexer_config=args.indexer_config,
        roles_config=args.roles_config,
        verbose=args.verbose,
    )


_parser = argparse.ArgumentParser(description="DataLoader CLI")

_parser.add_argument(
    "-wc",
    "--webloader-config",
    type=str,
    default="langchain_config.json",
    help="Path to the langchain config file (default: %(default)s)",
)
_parser.add_argument(
    "-ic",
    "--indexer-config",
    type=str,
    default="indexer_config.json",
    help="Path to the indexer config file (default: %(default)s)",
)
_parser.add_argument(
    "-rc",
    "--roles-config",
    type=str,
    default="role_config.json",
    help="Path to the roles config file (default: %(default)s)",
)
_parser.add_argument(
    "-v",
    "--verbose",
    action="store_true",
    help="Enable verbose logging",
)
