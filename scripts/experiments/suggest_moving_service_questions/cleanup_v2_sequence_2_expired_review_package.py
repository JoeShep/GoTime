"""Fixed CLI for dry-run or confirmed cleanup of one expired sequence-2 package."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from typing import Sequence

from v2_sequence_2_expired_review_cleanup import (
    CleanupError,
    cleanup_expired_sequence_2_review_package,
    verify_expired_sequence_2_review_package,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-sha256", required=True)
    parser.add_argument("--installation-record-sha256", required=True)
    parser.add_argument("--activation-review-sha256", required=True)
    parser.add_argument("--confirm-delete", action="store_true")
    parser.add_argument("--operator", default="")
    args = parser.parse_args(argv)
    now = datetime.now(timezone.utc)
    try:
        if args.confirm_delete:
            result = cleanup_expired_sequence_2_review_package(
                artifact_sha256=args.artifact_sha256,
                installation_record_sha256=args.installation_record_sha256,
                activation_review_sha256=args.activation_review_sha256,
                operator=args.operator, now=now,
            )
            for key, value in result.items():
                print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
        else:
            verified = verify_expired_sequence_2_review_package(
                artifact_sha256=args.artifact_sha256,
                installation_record_sha256=args.installation_record_sha256,
                activation_review_sha256=args.activation_review_sha256, now=now,
            )
            for path, digest in zip(verified.paths, verified.digests):
                print(f"delete_path={path.resolve()}")
                print(f"sha256={digest}")
            print(f"expired_at={verified.expires_at}")
            print("authoritative=false")
            print("activated=false")
            print("execution_manifest_closed=true")
            print("sequence_2_unused=true")
            print("dry_run=true")
    except (CleanupError, OSError):
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
