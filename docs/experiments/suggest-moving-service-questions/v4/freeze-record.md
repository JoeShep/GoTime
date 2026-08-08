# Prompt V4 Freeze Record

Prompt v4 makes only the approved instruction-salience changes after the single
frozen-v3 modality rejection. The historical field and trigger remain unknown.
The existing validator and fallback v2 are unchanged. Grounding remains byte-
exact, and prohibited grounding fails before provider-request construction.
The manifest-bound request-identity artifact freezes the deterministic request,
canonical attempt, and provider fingerprint for exact offline reproduction.
No provider operation or live v4 authorization exists.
