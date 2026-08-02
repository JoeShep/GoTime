# V2 Temporary-Storage Knowledge Reference

```text
status: draft_v2_reference_pending_human_review
source review preserved at:
  docs/experiments/suggest-moving-service-questions/v1/knowledge-source-review.md
knowledge fixture: moving-service-storage-fixture-v2
knowledge ID: moving-service.temporary-storage-planning.fmcsa.v1
```

V2 does not revise the curated knowledge item or its FMCSA source review. It
references the same approved conditional statement from the validated request:

> For an interstate move handled by a household-goods mover, a possible need
> for temporary storage before final delivery is relevant when identifying the
> services to request.

Prompt v2 requires `grounding_summary` to reproduce the supplied statement
exactly after JSON decoding. Runtime comparison uses the statement in the
validated request, not this document or the deterministic fallback.

The v2 deterministic storage fallback asks:

> Might you need temporary storage before final delivery?

This v2 reference does not modify the historical v1 review or broaden its
knowledge scope.
