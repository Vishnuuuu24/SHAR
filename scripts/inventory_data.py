#!/usr/bin/env python3
"""Build or calibrate the P0A local data inventory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data.inventory import build_inventory, calibrate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--calibrate-files", type=int, default=0)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    config = (args.config or repo_root / "data/registry/local_inventory.json").resolve()
    if args.workers < 1:
        parser.error("--workers must be at least 1")
    if args.calibrate_files:
        result = calibrate(repo_root, config, args.calibrate_files, args.workers)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ok_files"] == result["sample_files"] else 1
    output_root = (args.output_root or repo_root / "results/p0a").resolve()
    artifact = build_inventory(repo_root, config, output_root, args.workers)
    print(artifact)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
