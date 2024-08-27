import asyncio
import os

from cli.core.parser import parse_args

args = parse_args()
if args.verbose:
    os.environ["LOG_LEVEL"] = "DEBUG"

if __name__ == "__main__":
    from cli.main import main

    asyncio.run(main(args))
