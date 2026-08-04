"""Report future v2 preflight activation prerequisites without writing authority."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from run_openai_stage_b_v2_pilot import DEFAULT_OUTPUT_ROOT
from v2_preflight_authorization_installation import (
    ActivationPrerequisiteError, ClosedStateError, ConflictingStateError,
    ReviewValidationError, ValidityWindowError, plan_preflight_activation,
)


def main(
    argv: Sequence[str] | None = None, *, now: datetime | None = None,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> int:
    parser = argparse.ArgumentParser(description="Plan v2 preflight activation without performing it.")
    parser.add_argument("--artifact-sha256", required=True)
    parser.add_argument("--installation-record-sha256", required=True)
    parser.add_argument("--activation-review-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        result = plan_preflight_activation(
            artifact_sha256=args.artifact_sha256,
            installation_record_sha256=args.installation_record_sha256,
            activation_review_sha256=args.activation_review_sha256,
            output_root=output_root, now=now or datetime.now(timezone.utc),
        )
    except (ActivationPrerequisiteError, ClosedStateError, ConflictingStateError,
            ReviewValidationError, ValidityWindowError):
        print("activation_prerequisite_error: dry-run plan rejected", file=sys.stderr)
        return 12
    for key in (
        "source_installed_artifact", "future_active_destination",
        "expected_active_artifact_digest", "execution_manifest_transition_required",
        "execution_manifest_path", "closure_artifact", "remaining_operator_confirmations",
        "authoritative", "activated", "writes_performed", "activation_deadline",
    ):
        value = result[key]
        if isinstance(value, bool):
            value = str(value).lower()
        elif isinstance(value, list):
            value = json.dumps(value, separators=(",", ":"))
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
