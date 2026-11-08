"""Command-line entry point."""

import argparse
from typing import Optional, Sequence

from dotenv import load_dotenv

from .lichess_bot import run_bot


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="turochamp", description="Turochamp Lichess Bot & Engine")
    parser.add_argument("--depth", type=int, default=3, help="Search depth (default: 3)")
    args = parser.parse_args(argv)

    load_dotenv()
    run_bot(depth=args.depth)
    return 0
