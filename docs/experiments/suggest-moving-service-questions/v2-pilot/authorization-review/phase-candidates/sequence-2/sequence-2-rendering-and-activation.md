# Sequence-2 Preflight Rendering and Activation Boundary

The committed sequence-2 candidate and manifest are review inputs only. They
cannot authorize sequence 1, generation, or execution. The permanent closed
manifest remains authoritative until a separately approved atomic activation.

The previous host-Python command failed before creating an artifact because the
host environment did not contain Pydantic. Its timestamp package expired and
must not be reused. The reviewed operator flow now runs in the existing pinned
evaluation image with networking disabled; it does not require virtual-
environment activation or forward credentials.

The fixed renderer is:

```text
sh scripts/experiments/suggest_moving_service_questions/render_v2_sequence_2_preflight_authorization_candidate_docker.sh \
  --output /tmp/gotime-v2-sequence-2-preflight-authorization.toml \
  --approver "<APPROVER_ID>" \
  --approved-at "<APPROVED_AT_WHOLE_SECOND_UTC_Z>" \
  --activated-at "<ACTIVATED_AT_WHOLE_SECOND_UTC_Z>" \
  --expires-at "<EXPIRES_AT_WHOLE_SECOND_UTC_Z>" \
  --reason "<AUTHORIZATION_REASON>"
```

Installation, review, and planning use the fixed sequence-2 commands:

```text
python scripts/experiments/suggest_moving_service_questions/install_v2_sequence_2_preflight_authorization_for_review.py \
  --source /tmp/gotime-v2-sequence-2-preflight-authorization.toml \
  --expected-sha256 "<RENDERED_SHA256>"

python scripts/experiments/suggest_moving_service_questions/review_v2_sequence_2_preflight_authorization_activation.py \
  --artifact-sha256 "<INSTALLED_SHA256>" \
  --reviewer "<REVIEWER_ID>" --decision "<DECISION>" \
  --reviewed-at "<REVIEWED_AT_WHOLE_SECOND_UTC_Z>" --notes "<BOUNDED_NOTES>"

python scripts/experiments/suggest_moving_service_questions/plan_v2_sequence_2_preflight_authorization_activation.py \
  --artifact-sha256 "<INSTALLED_SHA256>" \
  --installation-record-sha256 "<INSTALLATION_RECORD_SHA256>" \
  --activation-review-sha256 "<ACTIVATION_REVIEW_SHA256>"
```

Only a later, explicit milestone may approve the fixed atomic activation command:

```text
python scripts/experiments/suggest_moving_service_questions/activate_v2_sequence_2_preflight_authorization.py \
  --artifact-sha256 "<INSTALLED_SHA256>" \
  --installation-record-sha256 "<INSTALLATION_RECORD_SHA256>" \
  --activation-review-sha256 "<ACTIVATION_REVIEW_SHA256>" \
  --operator "<OPERATOR_ID>" \
  --operator-intent "AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_PREFLIGHT_ONLY"
```

All local paths are fixed beneath run series
`moving-service-stage-b-v2-pilot-20260802` with prefix
`002-storage_unknown`. Synthetic activation tests verify dual binding between
the active authorization, execution manifest, activation evidence, and committed
journal; interruption recovery restores the exact permanent closed manifest.
No committed permission is active.

The launcher uses image `gotime-moving-service-stage-b:openai-2.45.0`, verifies
the locked OpenAI and Pydantic versions without downloading packages, mounts
the repository read-only, mounts host `/tmp` for the owner-only output, runs as
the host UID/GID, and passes only renderer arguments. Rendering remains non-
authoritative and never installs or activates the result.
