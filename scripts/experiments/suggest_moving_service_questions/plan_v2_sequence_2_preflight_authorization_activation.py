"""Plan fixed sequence-2 preflight activation without writing authority."""
from __future__ import annotations
import argparse, json, sys
from datetime import datetime, timezone
from typing import Sequence
from v2_sequence_2_preflight_authorization import plan_sequence_2_activation

def main(argv: Sequence[str] | None = None, *, now: datetime | None = None, output_root=None) -> int:
    parser = argparse.ArgumentParser()
    for name in ("artifact-sha256", "installation-record-sha256", "activation-review-sha256"): parser.add_argument(f"--{name}", required=True)
    args = parser.parse_args(argv)
    try:
        kwargs = {} if output_root is None else {"output_root": output_root}
        result = plan_sequence_2_activation(artifact_sha256=args.artifact_sha256, installation_record_sha256=args.installation_record_sha256, activation_review_sha256=args.activation_review_sha256, now=now or datetime.now(timezone.utc), **kwargs)
    except (OSError, ValueError):
        print("sequence_2_plan_error: activation plan rejected", file=sys.stderr); return 12
    for key, value in result.items():
        if isinstance(value, bool): value = str(value).lower()
        elif isinstance(value, list): value = json.dumps(value, separators=(",", ":"))
        print(f"{key}={value}")
    return 0

if __name__ == "__main__": raise SystemExit(main())
