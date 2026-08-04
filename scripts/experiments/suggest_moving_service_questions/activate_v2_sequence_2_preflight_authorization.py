"""Fixed sequence-2 atomic preflight activation CLI."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from typing import Sequence
from v2_sequence_2_preflight_authorization import activate_sequence_2_preflight

def main(argv: Sequence[str] | None = None, *, now: datetime | None = None, repository_root=None, output_root=None) -> int:
    parser = argparse.ArgumentParser()
    for name in ("artifact-sha256", "installation-record-sha256", "activation-review-sha256", "operator", "operator-intent"): parser.add_argument(f"--{name}", required=True)
    args = parser.parse_args(argv)
    kwargs = {}
    if repository_root is not None: kwargs["repository_root"] = repository_root
    if output_root is not None: kwargs["output_root"] = output_root
    try:
        result = activate_sequence_2_preflight(artifact_sha256=args.artifact_sha256, installation_record_sha256=args.installation_record_sha256, activation_review_sha256=args.activation_review_sha256, operator=args.operator, operator_intent=args.operator_intent, now=now or datetime.now(timezone.utc), **kwargs)
    except (OSError, ValueError): return 4
    for key, value in result.items(): print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0

if __name__ == "__main__": raise SystemExit(main())
