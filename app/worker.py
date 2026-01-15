from __future__ import annotations

import argparse

from .pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Clipmaker worker")
    parser.add_argument("--project_id", required=True)
    args = parser.parse_args()
    run_pipeline(args.project_id)


if __name__ == "__main__":
    main()
