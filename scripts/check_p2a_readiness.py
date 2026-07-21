#!/usr/bin/env python3
"""Report unresolved B-007 fields without loading data or running P2A."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.p2a_conventions import (
    ConventionValidationError,
    load_frozen_p2a_conventions,
    unresolved_convention_fields,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "config",
        nargs="?",
        type=Path,
        default=REPO_ROOT / "configs/p2a_scaffold.yaml",
    )
    args = parser.parse_args()
    try:
        unresolved = unresolved_convention_fields(args.config)
        if unresolved:
            print(f"B-007 NOT READY: {len(unresolved)} unresolved owner fields")
            for path in unresolved:
                print(f"- {path}")
            return 1
        frozen = load_frozen_p2a_conventions(args.config)
    except ConventionValidationError as exc:
        print(f"B-007 INVALID: {exc}", file=sys.stderr)
        return 2
    print(
        "B-007 CONFIG VALID: "
        f"10 degradations, {len(frozen.restoration_parameters)} restorations, "
        f"sha256={frozen.source_sha256}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
