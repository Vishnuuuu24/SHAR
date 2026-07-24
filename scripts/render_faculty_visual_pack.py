#!/usr/bin/env python3
"""Render the local, deterministic faculty visual-progress preview pack."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from data.faculty_visual_pack import render_faculty_visual_pack


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--config",
        type=Path,
        default=REPO_ROOT / "configs/faculty_progress_visual_pack.yaml",
    )
    args = parser.parse_args()
    print(render_faculty_visual_pack(args.repo_root, args.config))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
