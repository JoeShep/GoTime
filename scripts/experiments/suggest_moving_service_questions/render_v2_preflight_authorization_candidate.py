"""Render one reviewed v2 preflight candidate to /tmp without activating it."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence

from v2_phase_authorization_candidates import (
    RenderedPhaseAuthorization,
    V2PhaseCandidateError,
    load_inactive_phase_candidate,
    render_preflight_candidate,
)

EXIT_ARGUMENT_ERROR = 2
EXIT_PATH_POLICY_ERROR = 3
EXIT_CANDIDATE_INTEGRITY_ERROR = 4
EXIT_VALIDATION_ERROR = 5
EXIT_EXCLUSIVE_WRITE_ERROR = 6


class OutputPathPolicyError(ValueError):
    """The requested dry-run output path is outside the permitted boundary."""


class RenderingWriteError(OSError):
    """The exclusive dry-run write could not be completed."""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render the fixed inactive v2 preflight authorization candidate to /tmp."
    )
    parser.add_argument("--output", required=True)
    parser.add_argument("--approver", required=True)
    parser.add_argument("--approved-at", required=True)
    parser.add_argument("--activated-at", required=True)
    parser.add_argument("--expires-at", required=True)
    parser.add_argument("--reason", required=True)
    return parser


def validate_output_path(value: str) -> Path:
    """Return a safe absolute /tmp file path without following symlink components."""
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts:
        raise OutputPathPolicyError("output must be an absolute, traversal-free path under /tmp")
    lexical = Path(os.path.normpath(value))
    if lexical == Path("/tmp") or not lexical.is_relative_to(Path("/tmp")):
        raise OutputPathPolicyError("output must name a file beneath /tmp")
    current = Path("/")
    for component in lexical.parts[1:]:
        current /= component
        if current.exists() or current.is_symlink():
            if current.is_symlink():
                raise OutputPathPolicyError("output path must not contain symlinks")
    if lexical.exists() or lexical.is_symlink():
        raise OutputPathPolicyError("output file must not already exist")
    parent = lexical.parent
    if not parent.is_dir() or parent.is_symlink() or parent.resolve(strict=True) != parent:
        raise OutputPathPolicyError("output parent must resolve without symlinks")
    return lexical


def render_from_arguments(
    arguments: argparse.Namespace,
    *,
    now: datetime,
    loader: Callable[[str], object] = load_inactive_phase_candidate,
    renderer: Callable[..., RenderedPhaseAuthorization] = render_preflight_candidate,
) -> RenderedPhaseAuthorization:
    """Validate fixed repository inputs, then render one preflight-only file."""
    output = validate_output_path(arguments.output)
    try:
        loader("preflight")
    except (V2PhaseCandidateError, OSError, ValueError) as error:
        raise V2PhaseCandidateError("preflight candidate integrity verification failed") from error
    try:
        return renderer(
            output_path=output,
            approver=arguments.approver,
            approved_at=arguments.approved_at,
            activated_at=arguments.activated_at,
            expires_at=arguments.expires_at,
            authorization_reason=arguments.reason,
            now=now,
        )
    except FileExistsError as error:
        raise RenderingWriteError("exclusive output creation failed") from error
    except OSError as error:
        raise RenderingWriteError("exclusive output creation failed") from error


def main(
    argv: Sequence[str] | None = None,
    *,
    now: datetime | None = None,
    loader: Callable[[str], object] = load_inactive_phase_candidate,
    renderer: Callable[..., RenderedPhaseAuthorization] = render_preflight_candidate,
) -> int:
    parser = _parser()
    arguments = parser.parse_args(argv)
    try:
        rendered = render_from_arguments(
            arguments,
            now=now or datetime.now(timezone.utc),
            loader=loader,
            renderer=renderer,
        )
    except OutputPathPolicyError as error:
        print(f"path_policy_error: {error}", file=sys.stderr)
        return EXIT_PATH_POLICY_ERROR
    except RenderingWriteError as error:
        print(f"exclusive_write_error: {error}", file=sys.stderr)
        return EXIT_EXCLUSIVE_WRITE_ERROR
    except V2PhaseCandidateError as error:
        if error.__cause__ is not None and "integrity verification" in str(error):
            print("candidate_integrity_error: verification failed", file=sys.stderr)
            return EXIT_CANDIDATE_INTEGRITY_ERROR
        print(f"validation_error: {error}", file=sys.stderr)
        return EXIT_VALIDATION_ERROR
    print(f"output_path={rendered.path}")
    print(f"sha256={rendered.digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
