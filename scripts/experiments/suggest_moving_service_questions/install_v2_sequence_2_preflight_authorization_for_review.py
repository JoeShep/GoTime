"""Install the fixed sequence-2 preflight artifact for non-authoritative review."""
from __future__ import annotations
import argparse, sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence
from v2_sequence_2_preflight_authorization import install_sequence_2_for_review

def main(argv: Sequence[str] | None = None, *, now: datetime | None = None, output_root=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True); parser.add_argument("--expected-sha256", required=True)
    args = parser.parse_args(argv)
    try:
        kwargs = {} if output_root is None else {"output_root": output_root}
        result = install_sequence_2_for_review(source=Path(args.source), expected_sha256=args.expected_sha256, now=now or datetime.now(timezone.utc), **kwargs)
    except (OSError, ValueError):
        print("sequence_2_installation_error: review installation rejected", file=sys.stderr); return 4
    for key in ("installed_path", "sha256", "installation_record", "installation_record_sha256", "authoritative"):
        value = result[key]; print(f"{key}={str(value).lower() if isinstance(value, bool) else value}")
    return 0

if __name__ == "__main__": raise SystemExit(main())
