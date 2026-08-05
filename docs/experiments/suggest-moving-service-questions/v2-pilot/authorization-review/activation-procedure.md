# V2 Follow-Up Pilot Activation Procedure

This is a future procedure, not current authority. The inactive candidate must
never be copied over the permanent closed authorization in place.

1. Verify a clean working tree and frozen v1/v2 integrity.
2. Confirm the unchanged umbrella candidate SHA-256 digest and the selected
   inactive phase-candidate digest from `phase-candidates/phase-candidate-manifest.json`.
3. Resolve the exact approver and whole-second UTC approval, activation, and expiration timestamps.
4. Confirm sequence 1 is unused and no audit, evidence, deletion, or closure file conflicts exist.
5. Resolve every preflight-candidate placeholder and dry-run render a
   short-lived preflight-only artifact for review with:

   ```text
   python scripts/experiments/suggest_moving_service_questions/render_v2_preflight_authorization_candidate.py \
     --output /tmp/gotime-v2-preflight-authorization.toml \
     --approver "<APPROVER_ID>" \
     --approved-at "<APPROVED_AT_WHOLE_SECOND_UTC_Z>" \
     --activated-at "<ACTIVATED_AT_WHOLE_SECOND_UTC_Z>" \
     --expires-at "<EXPIRES_AT_WHOLE_SECOND_UTC_Z>" \
     --reason "<AUTHORIZATION_REASON>"
   ```

   This command only creates an owner-only `/tmp` review artifact and reports
   its digest. It does not install or activate the result. Verify that output
   against the phase-specific validator before proposing any manifest diff.
6. Install the exact rendered bytes into non-authoritative local review staging:

   ```text
   python scripts/experiments/suggest_moving_service_questions/install_v2_preflight_authorization_for_review.py \
     --source /tmp/gotime-v2-preflight-authorization.toml \
     --expected-sha256 "<RENDERED_ARTIFACT_SHA256>"
   ```

7. Record a separate activation review while the artifact remains valid:

   ```text
   python scripts/experiments/suggest_moving_service_questions/review_v2_preflight_authorization_activation.py \
     --artifact-sha256 "<INSTALLED_ARTIFACT_SHA256>" \
     --reviewer "<REVIEWER_ID>" \
     --decision approve \
     --reviewed-at "<WHOLE_SECOND_UTC_Z>" \
     --notes "<BOUNDED_NOTES>"
   ```

8. Run the non-writing activation planner with the exact artifact,
   installation-record, and activation-review digests. Review the proposed
   future active path and manifest transition. Installation, review approval,
   and planning do not activate authority.
9. In a separate future milestone, verify the preflight artifact digest,
   confirm generation remains false, and obtain approval to run exactly:

   ```text
   python scripts/experiments/suggest_moving_service_questions/activate_v2_preflight_authorization.py \
     --artifact-sha256 "<INSTALLED_ARTIFACT_SHA256>" \
     --installation-record-sha256 "<INSTALLATION_RECORD_SHA256>" \
     --activation-review-sha256 "<ACTIVATION_REVIEW_SHA256>" \
     --operator "<OPERATOR_ID>" \
     --operator-intent "activate exactly one v2 moving-service preflight authorization"
   ```

   Installation and review do not authorize this command. It atomically binds
   exact reviewed bytes to preflight-only repository authority only after a
   separate explicit approval.
10. Enter the evaluation credential interactively for the separately authorized preflight phase without displaying it:

   ```zsh
   read -s "GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY?OpenAI evaluation key: "
   echo
   export GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY
   ```

11. Run at most one preflight, unset the credential, close preflight authority, and review the persisted evidence and cost.
12. Resolve every generation-candidate placeholder and dry-run render a distinct
   short-lived generation-only artifact. Bind the evidence and review digests,
   token count, cost, request digest, canonical-attempt digest, provider
   fingerprint, reviewer, and review timestamp. Verify that evidence is fresh,
   approved, and unused before proposing any manifest diff.
13. Verify the generation artifact digest, confirm token preflight remains false, and obtain separate approval for that repository switch.
14. Re-enter the evaluation credential with the same silent zsh procedure and run at most one generation with zero retries; generation must not perform preflight.
15. Unset the credential and restore permanent closed authorization immediately.
16. Complete mandatory human grounding review.
17. Delete response evidence immediately after sign-off.
18. Verify permanent closed authorization and bounded closure evidence.

Operator intent, environment variables, and the inactive candidate are never
repository authority and cannot broaden the rendered active artifact.
The umbrella and both phase candidates remain committed review inputs only;
future active artifacts are distinct local files with independent digests and
must receive independent human approval and activation.
The rendering CLI supports preflight only; generation remains unavailable
until approved preflight evidence exists and a separate renderer is reviewed.

Sequence 1 is cancelled and consumed without a provider request. A future
package must authorize sequence 2. After its separate activation and live-call
approval, enter the credential with the documented zsh-safe commands, set
the exact operator controls, and run exactly:

```zsh
export GOTIME_MOVING_SERVICE_EVAL_ENABLED=1
export GOTIME_MOVING_SERVICE_EVAL_OPERATOR_INTENT=AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_PREFLIGHT_ONLY
sh scripts/experiments/suggest_moving_service_questions/run_openai_stage_b_v2_preflight_docker.sh
```

The launcher exposes no scope overrides and the preflight runner cannot invoke
generation. Closure follows the single attempt immediately.

Immediately before activation, reconfirm the current window, permanent closed
bytes, unused sequence, exact three input digests, and absence of active,
transaction, audit, evidence, consumption, cancellation, or closure conflicts.
Any interrupted transaction is non-runnable until the offline recovery path
restores exact closed state.

Sequence 2 uses the distinct candidate manifest and fixed commands documented
in `phase-candidates/sequence-2/sequence-2-rendering-and-activation.md`. Every
resolved and operational path uses prefix `002-storage_unknown`; no sequence-2
command accepts a sequence override or reads a `001` review record. Its exact
operator-intent literal is `AUTHORIZE_ONE_STORAGE_UNKNOWN_V2_PREFLIGHT_ONLY`.

The reviewed sequence-2 renderer must be invoked through its Docker launcher,
not host Python. It uses the pinned evaluation image with `--network none`,
forwards no credential environment variable, and writes only the requested
`/tmp` review artifact. The failed host-Python timestamp package created no
artifact and must not be reused; obtain fresh human-approved timestamps.
