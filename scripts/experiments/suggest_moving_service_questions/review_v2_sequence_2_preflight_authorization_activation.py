"""Review the fixed sequence-2 preflight installation without activating it."""
from __future__ import annotations
import argparse, sys
from datetime import datetime, timezone
from typing import Sequence
from v2_sequence_2_preflight_authorization import review_sequence_2_activation

def main(argv: Sequence[str] | None = None, *, now: datetime | None = None, output_root=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-sha256", required=True); parser.add_argument("--reviewer", required=True)
    parser.add_argument("--decision", choices=("approve", "reject", "request_changes"), required=True)
    parser.add_argument("--reviewed-at", required=True); parser.add_argument("--notes", required=True)
    args = parser.parse_args(argv)
    try:
        kwargs = {} if output_root is None else {"output_root": output_root}
        result = review_sequence_2_activation(artifact_sha256=args.artifact_sha256, reviewer=args.reviewer, decision=args.decision, reviewed_at=args.reviewed_at, notes=args.notes, now=now or datetime.now(timezone.utc), **kwargs)
    except (OSError, ValueError):
        print("sequence_2_review_error: activation review rejected", file=sys.stderr); return 10
    for key in ("review_path", "review_sha256", "decision", "authoritative", "activated"):
        value = result[key]; print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0

if __name__ == "__main__": raise SystemExit(main())
