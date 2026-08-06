"""Fixed sequence-2 closure and recovery CLI."""
from __future__ import annotations

import argparse
import hashlib
from datetime import datetime, timezone
from typing import Sequence

from v2_preflight_authorization_activation import activation_paths
from v2_sequence_2_preflight_authorization import recover_sequence_2_preflight


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--reason",
        required=True,
        choices=("success", "activation_recovery", "operator_cancellation", "expiration", "bounded_failure"),
    )
    args = parser.parse_args(argv)
    try:
        result = recover_sequence_2_preflight(reason=args.reason, now=datetime.now(timezone.utc))
        path = activation_paths(sequence=2).closure
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except (OSError, ValueError):
        return 4
    print(f"closure_path={path.resolve()}")
    print(f"closure_sha256={digest}")
    print(f"transaction_state={result['transaction_state']}")
    print(f"authorization_closed={str(result['authorization_closed']).lower()}")
    print("sequence=2")
    print("generation_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
