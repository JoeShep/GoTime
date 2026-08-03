# V2 Follow-Up Pilot Activation Procedure

This is a future procedure, not current authority. The inactive candidate must
never be copied over the permanent closed authorization in place.

1. Verify a clean working tree and frozen v1/v2 integrity.
2. Confirm the reviewed candidate SHA-256 digest.
3. Resolve the exact approver and whole-second UTC approval, activation, and expiration timestamps.
4. Confirm sequence 1 is unused and no audit, evidence, deletion, or closure file conflicts exist.
5. Render a separate short-lived active artifact and exact manifest diff through the reviewed lifecycle operation.
6. Verify the active artifact digest and all unrelated permissions remain false.
7. Obtain separate human approval for the repository switch, then apply only that reviewed switch.
8. Enter the evaluation credential interactively in zsh without displaying it:

   ```zsh
   read -s "GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY?OpenAI evaluation key: "
   echo
   export GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY
   ```

9. Run exactly one fresh token preflight and review its evidence and cost ceiling.
10. Obtain a separate generation approval or cancel.
11. Run at most one generation with zero retries.
12. Complete mandatory human grounding review.
13. Delete response evidence immediately after sign-off.
14. Restore and verify permanent closed authorization and bounded closure evidence.
15. Unset the evaluation credential in the bounded terminal.

Operator intent, environment variables, and the inactive candidate are never
repository authority and cannot broaden the rendered active artifact.
