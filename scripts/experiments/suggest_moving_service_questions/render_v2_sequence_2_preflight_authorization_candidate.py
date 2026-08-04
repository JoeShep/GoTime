"""Render the fixed inactive sequence-2 preflight candidate to /tmp only."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from typing import Sequence

from render_v2_preflight_authorization_candidate import (
    EXIT_ARGUMENT_ERROR,
    EXIT_CANDIDATE_INTEGRITY_ERROR,
    EXIT_EXCLUSIVE_WRITE_ERROR,
    EXIT_PATH_POLICY_ERROR,
    EXIT_VALIDATION_ERROR,
    OutputPathPolicyError,
    RenderingWriteError,
    validate_output_path,
)
from v2_phase_authorization_candidates import (
    V2PhaseCandidateError,
    render_preflight_candidate_for_sequence,
)
from v2_sequence_2_authorization_candidate import load_sequence_2_preflight_candidate


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        raise SystemExit(EXIT_ARGUMENT_ERROR)


def main(argv: Sequence[str] | None = None, *, now: datetime | None = None) -> int:
    parser = _Parser(description="Render the fixed inactive sequence-2 preflight candidate.")
    for name in ("output", "approver", "approved-at", "activated-at", "expires-at", "reason"):
        parser.add_argument(f"--{name}", required=True)
    args = parser.parse_args(argv)
    try:
        output = validate_output_path(args.output)
        load_sequence_2_preflight_candidate()
        rendered = render_preflight_candidate_for_sequence(
            sequence=2, candidate_loader=load_sequence_2_preflight_candidate,
            output_path=output, approver=args.approver, approved_at=args.approved_at,
            activated_at=args.activated_at, expires_at=args.expires_at,
            authorization_reason=args.reason, now=now or datetime.now(timezone.utc),
        )
    except OutputPathPolicyError as error:
        print(f"path_policy_error: {error}", file=sys.stderr)
        return EXIT_PATH_POLICY_ERROR
    except FileExistsError:
        print("exclusive_write_error: exclusive output creation failed", file=sys.stderr)
        return EXIT_EXCLUSIVE_WRITE_ERROR
    except RenderingWriteError:
        print("exclusive_write_error: exclusive output creation failed", file=sys.stderr)
        return EXIT_EXCLUSIVE_WRITE_ERROR
    except V2PhaseCandidateError:
        print("candidate_or_validation_error: sequence-2 rendering rejected", file=sys.stderr)
        return EXIT_CANDIDATE_INTEGRITY_ERROR
    except (OSError, ValueError):
        print("validation_error: sequence-2 rendering rejected", file=sys.stderr)
        return EXIT_VALIDATION_ERROR
    print(f"output_path={rendered.path}")
    print(f"sha256={rendered.digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
