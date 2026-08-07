# Sequence-4 rendering and activation boundary

Sequence 4 uses a distinct inactive candidate and fixed `004-storage_unknown`
paths. Sequences 1, 2, and 3 remain consumed historical records and cannot
authorize this sequence.

The committed candidate is inactive, placeholder-bound, non-authoritative, and preflight-only. Rendering, installation, activation review, planning, atomic activation, one live preflight, and closure remain separate operations.

Reviewed package digests:

- candidate: `a9a20f8933adfd63c0e6959795284c7287f4c1227cf976a4ac19e443c3b39f2c`
- candidate manifest: `a6ce4574ce8c787fb8cff511a264fa9f0e5a265c608e2496cf6ed42a701da125`

The future human operator live-call command is exactly:

```zsh
zsh scripts/experiments/suggest_moving_service_questions/run_v2_sequence_4_live_preflight_operator.zsh
```

The human operator must run it directly in the same interactive zsh that receives the silent credential prompt. Codex must not invoke it from a separate process. The script exports the evaluation-specific credential, enablement, and fixed operator intent only within its process tree, invokes the fixed sequence-4 Docker launcher once, verifies or recovers closure, and unsets all three variables on every exit path.

No credential is accepted as an argument or file. No generation request is authorized. The committed repository state remains closed.

After a successful preflight and verified closure, the bounded human evidence
review must be recorded with the fixed pinned command in the sequence-4
operator runbook before the evidence deadline and before the session ends.
