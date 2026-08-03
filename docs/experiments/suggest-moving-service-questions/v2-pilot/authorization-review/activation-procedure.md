# V2 Follow-Up Pilot Activation Procedure

This is a future procedure, not current authority. The inactive candidate must
never be copied over the permanent closed authorization in place.

1. Verify a clean working tree and frozen v1/v2 integrity.
2. Confirm the reviewed candidate SHA-256 digest.
3. Resolve the exact approver and whole-second UTC approval, activation, and expiration timestamps.
4. Confirm sequence 1 is unused and no audit, evidence, deletion, or closure file conflicts exist.
5. Render a short-lived preflight-only artifact and exact manifest diff through the reviewed lifecycle operation.
6. Verify the preflight artifact digest, confirm generation remains false, and obtain approval for that repository switch.
7. Enter the evaluation credential interactively for the separately authorized preflight phase without displaying it:

   ```zsh
   read -s "GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY?OpenAI evaluation key: "
   echo
   export GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY
   ```

8. Run at most one preflight, unset the credential, close preflight authority, and review the persisted evidence and cost.
9. Render a distinct short-lived generation-only artifact bound to the approved evidence and review digests.
10. Verify the generation artifact digest, confirm token preflight remains false, and obtain separate approval for that repository switch.
11. Re-enter the evaluation credential with the same silent zsh procedure and run at most one generation with zero retries; generation must not perform preflight.
12. Unset the credential and restore permanent closed authorization immediately.
13. Complete mandatory human grounding review.
14. Delete response evidence immediately after sign-off.
15. Verify permanent closed authorization and bounded closure evidence.

Operator intent, environment variables, and the inactive candidate are never
repository authority and cannot broaden the rendered active artifact.
