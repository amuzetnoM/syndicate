"""Orchestrator CLI for one-shot ingest runs (skeleton)

Usage:
    python -m ingest_bot.orchestrator --once --source fred
"""
import argparse
import logging
from datetime import datetime

from .adapters import fred
from .pipeline.writer import write_ingest_records

LOG = logging.getLogger("ingest_bot.orchestrator")


def run_once(source: str):
    LOG.info("Running one-shot ingest for source=%s", source)
    # Read manifest to decide since timestamp (skeleton uses epoch)
    since = "1970-01-01T00:00:00Z"
    if source == "fred":
        records = fred.fetch_since(since)
    else:
        LOG.warning("Unknown source %s — no-op", source)
        records = []
    write_ingest_records(source, records)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run a single ingest and exit")
    parser.add_argument("--source", required=True)
    args = parser.parse_args(argv)

    if args.once:
        run_once(args.source)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
