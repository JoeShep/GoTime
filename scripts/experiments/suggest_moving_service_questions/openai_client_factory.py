"""Closed credential and OpenAI client boundary for the moving-service evaluation.

The public entry point verifies the exact repository authorization before it
touches the supplied environment mapping. The current authorization is closed,
so no credential can be read and no client can be constructed through it.
Internal seams are dependency-injected for offline tests only.
"""

from __future__ import annotations

import hashlib
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Protocol


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EXECUTION_AUTHORIZATION_PATH = (
    REPOSITORY_ROOT
    / "docs/experiments/suggest-moving-service-questions/v1/"
    "openai-execution-authorization.toml"
)
DEFAULT_MANIFEST_PATH = (
    REPOSITORY_ROOT
    / "docs/experiments/suggest-moving-service-questions/v1/manifest.json"
)
EXECUTION_AUTHORIZATION_DIGEST = (
    "6e3ca9cb4488764f012703ab77daae4f4b952895100f7d935935aeb6a0978be5"
)
EVALUATION_CREDENTIAL_NAME = "GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY"
OPENAI_SDK_VERSION = "2.45.0"
OPENAI_API_BASE_URL = "https://api.openai.com/v1"
MAXIMUM_CREDENTIAL_LENGTH = 4_096
REQUIRED_NON_SECRET_GATE_ORDER = (
    "artifact_integrity",
    "repository_authorization",
    "fixture_and_sequence_validation",
    "output_path_checks",
    "budget_checks",
    "operator_intent_check",
)
CONVENTIONAL_OPENAI_ENVIRONMENT_NAMES = frozenset(
    {
        "OPENAI_API_KEY",
        "OPENAI_ADMIN_KEY",
        "OPENAI_ORG_ID",
        "OPENAI_PROJECT_ID",
        "OPENAI_WEBHOOK_SECRET",
        "OPENAI_BASE_URL",
    }
)
_CREDENTIAL_CONSTRUCTION_TOKEN = object()


class CredentialBoundaryError(ValueError):
    """The evaluation credential boundary failed closed."""


class CredentialAccessNotAuthorizedError(CredentialBoundaryError):
    """Repository authorization does not permit credential access."""


class EvaluationCredentialError(CredentialBoundaryError):
    """The synthetic or future evaluation credential is invalid."""


class OpenAIClientConstructionError(CredentialBoundaryError):
    """The pinned, capability-specific client could not be constructed."""


class _ClientLike(Protocol):
    max_retries: int

    def close(self) -> None:
        ...


class _HttpClientLike(Protocol):
    def close(self) -> None:
        ...


class MovingServiceEvaluationCredential:
    """Non-serializable secret wrapper with redacted text representations."""

    __slots__ = ("__value",)

    def __init__(self, value: str, token: object) -> None:
        if token is not _CREDENTIAL_CONSTRUCTION_TOKEN:
            raise TypeError("Evaluation credentials must come from the credential reader.")
        self.__value = value

    def __repr__(self) -> str:
        return "MovingServiceEvaluationCredential(<redacted>)"

    __str__ = __repr__

    def __reduce__(self) -> object:
        raise TypeError("Evaluation credentials cannot be serialized.")

    def _reveal_for_client_construction(self) -> str:
        return self.__value


class MovingServiceOpenAIClient:
    """Owns the capability-specific SDK client and its HTTP client."""

    __slots__ = ("client", "_http_client", "_closed")

    def __init__(self, client: _ClientLike, http_client: _HttpClientLike) -> None:
        self.client = client
        self._http_client = http_client
        self._closed = False

    def __repr__(self) -> str:
        return "MovingServiceOpenAIClient(<closed>)" if self._closed else (
            "MovingServiceOpenAIClient(<open>)"
        )

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.client.close()
        finally:
            self._http_client.close()

    def __enter__(self) -> MovingServiceOpenAIClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _require_credential_access_authorized(
    manifest_path: Path,
    authorization_path: Path,
    expected_digest: str,
) -> None:
    from stage_a_authorization import (
        StageAAuthorizationError,
        load_manifest_bound_stage_a_authorization,
    )

    if manifest_path.resolve() != DEFAULT_MANIFEST_PATH.resolve():
        raise CredentialAccessNotAuthorizedError(
            "Credential access requires the repository's active manifest."
        )
    try:
        verified = load_manifest_bound_stage_a_authorization(
            manifest_path,
            repository_root=REPOSITORY_ROOT,
        )
    except StageAAuthorizationError as error:
        raise CredentialAccessNotAuthorizedError(str(error)) from error
    if (
        verified.path.resolve() != authorization_path.resolve()
        or verified.digest != expected_digest
    ):
        raise CredentialAccessNotAuthorizedError(
            "Credential authorization is not the manifest-bound Stage A artifact."
        )
    artifact_bytes = authorization_path.read_bytes()
    if hashlib.sha256(artifact_bytes).hexdigest() != expected_digest:
        raise CredentialAccessNotAuthorizedError(
            "Execution authorization failed integrity verification."
        )
    try:
        artifact = tomllib.loads(artifact_bytes.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise CredentialAccessNotAuthorizedError(
            "Execution authorization is not parseable."
        ) from error
    permissions = artifact.get("authorization")
    if not isinstance(permissions, dict):
        raise CredentialAccessNotAuthorizedError(
            "Execution authorization permissions are missing."
        )
    expected_permission_fields = {
        "credential_access_authorized",
        "token_preflight_authorized",
        "ai_generation_authorized",
        "formal_evaluation_authorized",
    }
    if set(permissions) != expected_permission_fields:
        raise CredentialAccessNotAuthorizedError(
            "Execution authorization permissions are incompatible."
        )
    if permissions["credential_access_authorized"] is not True:
        raise CredentialAccessNotAuthorizedError(
            "Repository authorization does not permit credential access."
        )
    metadata = artifact.get("metadata")
    approval = artifact.get("approval")
    if not isinstance(metadata, dict) or not isinstance(approval, dict):
        raise CredentialAccessNotAuthorizedError(
            "Active execution authorization metadata is missing."
        )
    if metadata.get("active_repository_authority") is not True:
        raise CredentialAccessNotAuthorizedError(
            "Execution authorization is not active repository authority."
        )
    if metadata.get("authorization_status") != "approved_stage_a_token_preflight":
        raise CredentialAccessNotAuthorizedError(
            "Execution authorization status is not approved for Stage A."
        )
    if approval.get("approval_status") != "approved":
        raise CredentialAccessNotAuthorizedError(
            "Execution authorization has not been approved."
        )
    approved_by = approval.get("approved_by")
    if (
        not isinstance(approved_by, str)
        or not approved_by.strip()
        or approved_by == "pending"
    ):
        raise CredentialAccessNotAuthorizedError(
            "Execution authorization approving identity is invalid."
        )
    try:
        approved_at = datetime.fromisoformat(
            str(approval["approved_at"]).replace("Z", "+00:00")
        )
        expires_at = datetime.fromisoformat(
            str(approval["expires_at"]).replace("Z", "+00:00")
        )
    except (KeyError, ValueError) as error:
        raise CredentialAccessNotAuthorizedError(
            "Execution authorization approval window is invalid."
        ) from error
    now = datetime.now(timezone.utc)
    if approved_at.tzinfo is None or expires_at.tzinfo is None:
        raise CredentialAccessNotAuthorizedError(
            "Execution authorization timestamps must include UTC offsets."
        )
    maximum_duration = approval.get("maximum_authorization_duration_seconds")
    if maximum_duration != 900 or not approved_at <= now < expires_at:
        raise CredentialAccessNotAuthorizedError(
            "Execution authorization is outside its approved window."
        )
    if (expires_at - approved_at).total_seconds() > maximum_duration:
        raise CredentialAccessNotAuthorizedError(
            "Execution authorization window is too long."
        )


def _read_evaluation_credential(
    environment: Mapping[str, str],
) -> MovingServiceEvaluationCredential:
    present_conventional_names = sorted(
        name for name in CONVENTIONAL_OPENAI_ENVIRONMENT_NAMES if name in environment
    )
    if present_conventional_names:
        raise EvaluationCredentialError(
            "Conventional OpenAI environment configuration is prohibited."
        )
    value = environment.get(EVALUATION_CREDENTIAL_NAME)
    if value is None:
        raise EvaluationCredentialError("The evaluation credential is missing.")
    if not isinstance(value, str) or not value.strip():
        raise EvaluationCredentialError("The evaluation credential is blank.")
    if "\n" in value or "\r" in value:
        raise EvaluationCredentialError("The evaluation credential is multiline.")
    if len(value) > MAXIMUM_CREDENTIAL_LENGTH:
        raise EvaluationCredentialError("The evaluation credential is too long.")
    return MovingServiceEvaluationCredential(value, _CREDENTIAL_CONSTRUCTION_TOKEN)


def _construct_openai_client(
    credential: MovingServiceEvaluationCredential,
    *,
    sdk_version: str,
    client_constructor: Callable[..., _ClientLike],
    http_client_constructor: Callable[..., _HttpClientLike],
) -> MovingServiceOpenAIClient:
    if sdk_version != OPENAI_SDK_VERSION:
        raise OpenAIClientConstructionError("The OpenAI SDK version is incompatible.")
    http_client = http_client_constructor(trust_env=False)
    try:
        client = client_constructor(
            api_key=credential._reveal_for_client_construction(),
            base_url=OPENAI_API_BASE_URL,
            max_retries=0,
            http_client=http_client,
        )
    except Exception:
        http_client.close()
        raise OpenAIClientConstructionError(
            "The OpenAI client constructor failed."
        ) from None
    if client.max_retries != 0:
        try:
            client.close()
        finally:
            http_client.close()
        raise OpenAIClientConstructionError("The OpenAI client enabled retries.")
    return MovingServiceOpenAIClient(client, http_client)


def build_moving_service_openai_client_from_environment(
    environment: Mapping[str, str],
    *,
    completed_non_secret_gates: tuple[str, ...],
    operator_intent_confirmed: bool,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    authorization_path: Path = DEFAULT_EXECUTION_AUTHORIZATION_PATH,
    expected_authorization_digest: str = EXECUTION_AUTHORIZATION_DIGEST,
    sdk_version: str = OPENAI_SDK_VERSION,
    client_constructor: Callable[..., _ClientLike],
    http_client_constructor: Callable[..., _HttpClientLike],
) -> MovingServiceOpenAIClient:
    """Fail closed before touching the environment under current authority."""
    if completed_non_secret_gates != REQUIRED_NON_SECRET_GATE_ORDER:
        raise CredentialAccessNotAuthorizedError(
            "The ordered non-secret runner gates are incomplete."
        )
    if operator_intent_confirmed is not True:
        raise CredentialAccessNotAuthorizedError(
            "Explicit operator intent was not confirmed."
        )
    _require_credential_access_authorized(
        manifest_path,
        authorization_path,
        expected_authorization_digest,
    )
    credential = _read_evaluation_credential(environment)
    return _construct_openai_client(
        credential,
        sdk_version=sdk_version,
        client_constructor=client_constructor,
        http_client_constructor=http_client_constructor,
    )


def build_moving_service_openai_client_with_pinned_sdk(
    environment: Mapping[str, str],
    *,
    completed_non_secret_gates: tuple[str, ...],
    operator_intent_confirmed: bool,
    manifest_path: Path,
    authorization_path: Path,
    expected_authorization_digest: str,
) -> MovingServiceOpenAIClient:
    """Bind the official pinned constructors only after authorization checks."""
    if completed_non_secret_gates != REQUIRED_NON_SECRET_GATE_ORDER:
        raise CredentialAccessNotAuthorizedError(
            "The ordered non-secret runner gates are incomplete."
        )
    if operator_intent_confirmed is not True:
        raise CredentialAccessNotAuthorizedError(
            "Explicit operator intent was not confirmed."
        )
    _require_credential_access_authorized(
        manifest_path,
        authorization_path,
        expected_authorization_digest,
    )
    from openai import DefaultHttpxClient, OpenAI

    credential = _read_evaluation_credential(environment)
    return _construct_openai_client(
        credential,
        sdk_version=OPENAI_SDK_VERSION,
        client_constructor=OpenAI,
        http_client_constructor=DefaultHttpxClient,
    )
