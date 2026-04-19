"""CLI entry point for procwatch."""

import argparse
import logging
import sys

from procwatch.config import load
from procwatch.supervisor import Supervisor


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="procwatch",
        description="Monitor and restart failing processes.",
    )
    parser.add_argument(
        "config",
        metavar="CONFIG",
        help="Path to TOML configuration file.",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose (DEBUG) logging.",
    )
    return parser


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    setup_logging(args.verbose)

    logger = logging.getLogger("procwatch.cli")

    try:
        config = load(args.config)
    except FileNotFoundError:
        logger.error("Config file not found: %s", args.config)
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to load config: %s", exc)
        sys.exit(1)

    logger.info("Loaded %d process(es) from %s", len(config.processes), args.config)
    supervisor = Supervisor(config)
    supervisor.run_forever()


if __name__ == "__main__":
    main()
