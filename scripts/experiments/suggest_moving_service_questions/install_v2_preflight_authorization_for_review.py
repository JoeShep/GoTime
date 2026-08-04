"""Install one rendered v2 preflight artifact into non-authoritative review staging."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from run_openai_stage_b_v2_pilot import DEFAULT_OUTPUT_ROOT
from v2_preflight_authorization_installation import (
    ClosedStateError, ConflictingStateError, InstallationPathError,
    InstallationWriteError, PackageIntegrityError, SourceIntegrityError,
    ValidityWindowError, install_preflight_for_review,
)


def main(
    argv: Sequence[str] | None = None, *, now: datetime | None = None,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
) -> int:
    parser = argparse.ArgumentParser(description="Install a rendered v2 preflight artifact for review only.")
    parser.add_argument("--source", required=True)
    parser.add_argument("--expected-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        result = install_preflight_for_review(
            source=Path(args.source), expected_sha256=args.expected_sha256,
            output_root=output_root, now=now or datetime.now(timezone.utc),
        )
    except InstallationPathError:
        print("path_policy_error: source path rejected", file=sys.stderr)
        return 3
    except SourceIntegrityError:
        print("source_integrity_error: rendered source rejected", file=sys.stderr)
        return 4
    except PackageIntegrityError:
        print("candidate_integrity_error: reviewed package rejected", file=sys.stderr)
        return 5
    except ClosedStateError:
        print("closed_state_error: permanent closed state not verified", file=sys.stderr)
        return 6
    except ConflictingStateError:
        print("conflicting_state_error: local state conflict", file=sys.stderr)
        return 7
    except ValidityWindowError:
        print("validity_window_error: rendered authorization is not currently valid", file=sys.stderr)
        return 8
    except InstallationWriteError:
        print("installation_write_error: exclusive staging failed", file=sys.stderr)
        return 9
    for key in (
        "installed_path", "sha256", "installation_record",
        "installation_record_sha256", "authoritative",
    ):
        print(f"{key}={str(result[key]).lower() if isinstance(result[key], bool) else result[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
