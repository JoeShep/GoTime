"""Network-free phase separation proof invoked by the exact Docker launchers."""

from __future__ import annotations

import os
import sys

from openai_client_factory import EVALUATION_CREDENTIAL_NAME


class FakeResponses:
    def __init__(self) -> None:
        self.preflight_calls = 0
        self.generation_calls = 0

    def count(self) -> None:
        self.preflight_calls += 1

    def create(self) -> None:
        self.generation_calls += 1


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {"preflight", "generation"}:
        return 2
    assert os.environ.get(EVALUATION_CREDENTIAL_NAME)
    responses = FakeResponses()
    if sys.argv[1] == "preflight":
        responses.count()
        assert responses.preflight_calls == 1 and responses.generation_calls == 0
    else:
        responses.create()
        assert responses.preflight_calls == 0 and responses.generation_calls == 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
