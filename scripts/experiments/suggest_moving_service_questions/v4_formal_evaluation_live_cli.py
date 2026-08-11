#!/usr/bin/env python3
"""Six-command offline CLI for aggregate coordination only."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from v4_formal_evaluation_live_deterministic import resolve_deterministic_cases
from v4_formal_evaluation_live_models import immutable_package, package_identity
from v4_formal_evaluation_live_state import AggregateStore, default_root

PUBLIC_COMMANDS = (
    "verify-foundation", "initialize", "inspect", "verify",
    "resolve-deterministic-cases", "close",
)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Coordinate frozen-v4 formal evaluation state offline")
    result.add_argument("--state-root", type=Path, default=default_root())
    commands = result.add_subparsers(dest="command", required=True)
    commands.add_parser("verify-foundation")
    initialize = commands.add_parser("initialize")
    initialize.add_argument("--operator", required=True)
    initialize.add_argument("--reviewer", required=True)
    inspect = commands.add_parser("inspect")
    inspect.add_argument("--resume", action="store_true")
    inspect.add_argument("--reviewer")
    commands.add_parser("verify")
    commands.add_parser("resolve-deterministic-cases")
    close = commands.add_parser("close")
    close.add_argument("--reviewer", required=True)
    close.add_argument("--abandon", action="store_true")
    return result


def main() -> int:
    arguments = parser().parse_args()
    store = AggregateStore(arguments.state_root)
    if arguments.command == "verify-foundation":
        immutable_package()
        output = {"aggregate_id": immutable_package()["aggregate_id"], "package_identity_sha256": package_identity(), "provider_authority": False, "ready": True}
    elif arguments.command == "initialize":
        output = store.initialize(arguments.operator, arguments.reviewer)
    elif arguments.command == "inspect":
        if arguments.resume:
            if not arguments.reviewer:
                raise SystemExit("--reviewer is required with --resume")
            output = store.resume(arguments.reviewer)
        else:
            output = store.load()
    elif arguments.command == "verify":
        state = store.load()
        output = {"aggregate_id": state["aggregate_id"], "history_head_sha256": state["history_head_sha256"], "status": state["status"], "valid": True, "provider_authority": False}
    elif arguments.command == "resolve-deterministic-cases":
        output = resolve_deterministic_cases(store)
    else:
        output = store.close(arguments.reviewer, abandon=arguments.abandon)
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
