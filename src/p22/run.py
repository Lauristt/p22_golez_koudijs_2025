"""Small command-line dispatcher for independently rebuildable pipeline stages."""

import argparse


def main():
    """Run exactly one named ingestion, estimation, plotting or validation stage."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage")
    parser.add_argument("group", nargs="?")
    args = parser.parse_args()
    if args.stage == "fetch":
        from .fetch import fetch

        fetch()
    elif args.stage == "ingest":
        from .ingest import ingest

        ingest(args.group)
    elif args.stage in ["strips", "history", "portfolios"]:
        from importlib import import_module

        import_module("p22." + args.stage).calculate()
    elif args.stage in ["payout", "summary"]:
        from . import figures

        getattr(figures, args.stage)()
    elif args.stage in ["validate", "report", "provenance"]:
        from . import validation

        getattr(validation, args.stage)()
    else:
        parser.error("Unknown stage")


if __name__ == "__main__":
    main()
