"""Record a bounded, non-activating review of the installed preflight artifact."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from run_openai_stage_b_v2_pilot import DEFAULT_OUTPUT_ROOT
from v2_preflight_authorization_installation import (
    ClosedStateError, ConflictingStateError, DECISIONS, ReviewValidationError,
    ReviewWriteError, ValidityWindowError, review_preflight_activation,
)


def main(
    argv: Sequence[str] | None = None, *, now: datetime | None = None,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> int:
    parser = argparse.ArgumentParser(description="Review installed v2 preflight authority without activating it.")
    parser.add_argument("--artifact-sha256", required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--decision", required=True, choices=sorted(DECISIONS))
    parser.add_argument("--reviewed-at", required=True)
    parser.add_argument("--notes", required=True)
    args = parser.parse_args(argv)
    try:
        result = review_preflight_activation(
            artifact_sha256=args.artifact_sha256, reviewer=args.reviewer,
            decision=args.decision, reviewed_at=args.reviewed_at, notes=args.notes,
            output_root=output_root, now=now or datetime.now(timezone.utc),
        )
    except ClosedStateError:
        print("closed_state_error: permanent closed state not verified", file=sys.stderr)
        return 6
    except ConflictingStateError:
        print("conflicting_state_error: local state conflict", file=sys.stderr)
        return 7
    except ValidityWindowError:
        print("validity_window_error: installed authorization is not currently valid", file=sys.stderr)
        return 8
    except ReviewValidationError:
        print("review_validation_error: activation review rejected", file=sys.stderr)
        return 10
    except ReviewWriteError:
        print("review_write_error: exclusive review write failed", file=sys.stderr)
        return 11
    for key in ("review_path", "review_sha256", "decision", "authoritative", "activated"):
        print(f"{key}={str(result[key]).lower() if isinstance(result[key], bool) else result[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
