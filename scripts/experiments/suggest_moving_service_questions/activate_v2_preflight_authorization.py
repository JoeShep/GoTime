"""Capability-specific atomic activation CLI for the v2 preflight phase."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from run_openai_stage_b_v2_pilot import DEFAULT_OUTPUT_ROOT
from v2_preflight_authorization_activation import (
    REPOSITORY_ROOT,
    ActivationClosedStateError,
    ActivationConflictError,
    ActivationReviewError,
    ActivationValidityError,
    ActiveAuthorizationWriteError,
    ActivationRecordWriteError,
    InputIntegrityError,
    ManifestTransitionError,
    RecoveryRequiredError,
    TransactionCommitError,
    TransactionPreparationError,
    activate_preflight_authorization,
)

EXIT_ARGUMENT = 2
EXIT_INPUT_INTEGRITY = 3
EXIT_REVIEW_VALIDATION = 4
EXIT_VALIDITY_WINDOW = 5
EXIT_CLOSED_STATE = 6
EXIT_CONFLICTING_STATE = 7
EXIT_TRANSACTION_PREPARATION = 8
EXIT_ACTIVE_AUTHORIZATION_WRITE = 9
EXIT_MANIFEST_TRANSITION = 10
EXIT_ACTIVATION_RECORD_WRITE = 11
EXIT_TRANSACTION_COMMIT = 12
EXIT_RECOVERY_REQUIRED = 13


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        raise SystemExit(EXIT_ARGUMENT)


def main(
    argv: Sequence[str] | None = None, *, now: datetime | None = None,
    repository_root: Path = REPOSITORY_ROOT, output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> int:
    parser = _Parser()
    parser.add_argument("--artifact-sha256", required=True)
    parser.add_argument("--installation-record-sha256", required=True)
    parser.add_argument("--activation-review-sha256", required=True)
    parser.add_argument("--operator", required=True)
    parser.add_argument("--operator-intent", required=True)
    args = parser.parse_args(argv)
    try:
        result = activate_preflight_authorization(
            artifact_sha256=args.artifact_sha256,
            installation_record_sha256=args.installation_record_sha256,
            activation_review_sha256=args.activation_review_sha256,
            operator=args.operator, operator_intent=args.operator_intent,
            now=now or datetime.now(timezone.utc), repository_root=repository_root,
            output_root=output_root,
        )
    except InputIntegrityError:
        return EXIT_INPUT_INTEGRITY
    except ActivationReviewError:
        return EXIT_REVIEW_VALIDATION
    except ActivationValidityError:
        return EXIT_VALIDITY_WINDOW
    except ActivationClosedStateError:
        return EXIT_CLOSED_STATE
    except ActivationConflictError:
        return EXIT_CONFLICTING_STATE
    except TransactionPreparationError:
        return EXIT_TRANSACTION_PREPARATION
    except ActiveAuthorizationWriteError:
        return EXIT_ACTIVE_AUTHORIZATION_WRITE
    except ManifestTransitionError:
        return EXIT_MANIFEST_TRANSITION
    except ActivationRecordWriteError:
        return EXIT_ACTIVATION_RECORD_WRITE
    except TransactionCommitError:
        return EXIT_TRANSACTION_COMMIT
    except RecoveryRequiredError:
        return EXIT_RECOVERY_REQUIRED
    for key in (
        "active_authorization", "active_authorization_sha256", "execution_manifest_sha256",
        "activation_record", "activation_record_sha256", "transaction_id",
        "transaction_state", "phase", "generation_authorized",
    ):
        value = result[key]
        if isinstance(value, bool):
            value = str(value).lower()
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
