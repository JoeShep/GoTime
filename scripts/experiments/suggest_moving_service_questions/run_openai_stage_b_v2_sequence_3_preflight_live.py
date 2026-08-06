"""Future-live, single-use sequence-3 token-preflight entry point."""

from __future__ import annotations

from run_openai_stage_b_v2_preflight_live import run as _run
from v2_preflight_authorization_activation import load_active_preflight_authorization, recover_preflight_activation


def run(**kwargs):
    kwargs.setdefault("active_loader", load_active_preflight_authorization)
    kwargs.setdefault("closure_operation", recover_preflight_activation)
    return _run(sequence=3, **kwargs)


def main() -> int:
    run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
