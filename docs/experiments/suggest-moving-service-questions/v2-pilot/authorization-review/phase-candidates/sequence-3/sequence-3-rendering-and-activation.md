# Sequence-3 rendering and activation boundary

Sequence 3 uses a distinct inactive candidate and fixed `003-storage_unknown` paths. Sequence 1 and sequence 2 remain consumed historical records and cannot authorize this sequence.

The committed candidate is inactive, placeholder-bound, non-authoritative, and preflight-only. Rendering, installation, activation review, planning, atomic activation, one live preflight, and closure remain separate operations.

The future human operator live-call command is exactly:

```zsh
zsh scripts/experiments/suggest_moving_service_questions/run_v2_sequence_3_live_preflight_operator.zsh
```

The human operator must run it directly in the same interactive zsh that receives the silent credential prompt. Codex must not invoke it from a separate process. The script exports the evaluation-specific credential, enablement, and fixed operator intent only within its process tree, invokes the fixed sequence-3 Docker launcher once, verifies or recovers closure, and unsets all three variables on every exit path.

No credential is accepted as an argument or file. No generation request is authorized. The committed repository state remains closed.
