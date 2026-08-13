from __future__ import annotations

import json
import os
import subprocess
import shutil
import signal
import stat
import textwrap
from datetime import timedelta
from pathlib import Path

import pytest

from test_v4_formal_evaluation_live_generation import generation_ready, ready
from v4_formal_evaluation_live_execution import (
    CREDENTIAL, ExecutionBoundaryError, ProviderExecutionBoundary, SDK_PIN,
)
from v4_formal_evaluation_live_state import AggregateStateError, AggregateStore

FAKE = "synthetic-m8-credential-never-log"


class FakeClient:
    def __init__(self, **kwargs):
        self.arguments = kwargs
        self.max_retries = kwargs["max_retries"]
        self.closed = False

    def close(self): self.closed = True


class FakeHttpClient:
    def __init__(self, **kwargs): self.arguments = kwargs; self.closed = False
    def close(self): self.closed = True


class SyntheticBoundary(ProviderExecutionBoundary):
    def __init__(self, *args, fail=None, **kwargs):
        super().__init__(*args, **kwargs); self.calls = 0; self.fail = fail

    def _live_readiness_authorized(self, phase, state):
        return True

    def _client_constructors(self):
        return FakeClient, FakeHttpClient

    def _enter_provider(self, prepared, client):
        state = self.store.load()
        assert client.client.max_retries == 0
        assert client.client.arguments["max_retries"] == 0
        assert client._http_client.arguments == {"trust_env": False}
        assert prepared.request_configuration["automatic_retries"] == 0
        assert prepared.timeout_seconds == 5
        assert state["provider_budget_reservations"][prepared.case_id]["lifecycle"]["status"] == "consumed"
        self.calls += 1
        if self.fail: raise self.fail
        return {"input_tokens": 2852}


def prepared_store(tmp_path):
    root = tmp_path / "state"
    from test_v4_formal_evaluation_live_generation import Clock
    from v4_formal_evaluation_live_deterministic import resolve_deterministic_cases
    clock = Clock(); store = AggregateStore(root, clock)
    store.initialize("Operator", "Reviewer"); store.resume("Reviewer")
    resolve_deterministic_cases(store); store.bind_ai_case_envelopes()
    store.prepare_preflight_grant(); store.authorize_preflight_budget()
    return store, clock


def test_production_precheck_is_closed_and_generation_evidence_precedes_live_gate(tmp_path):
    store, _ = prepared_store(tmp_path); before = store.load(); journal = store._read_journal()
    with pytest.raises(ExecutionBoundaryError, match="live provider execution authorization"):
        ProviderExecutionBoundary(store, {}).precheck("preflight")
    with pytest.raises(ExecutionBoundaryError, match="reviewed production preflight evidence"):
        ProviderExecutionBoundary(store, {}).precheck("generation")
    assert store.load() == before and store._read_journal() == journal


def test_synthetic_generation_precheck_binds_exact_active_evidence_and_reservation(tmp_path):
    store, _ = generation_ready(tmp_path); state = store._authorize_generation_budget()
    prepared = SyntheticBoundary(store, {CREDENTIAL: FAKE}).precheck("generation")
    assert prepared.phase == "generation" and prepared.case_id == "eval-v4-01"
    assert prepared.grant_sha256 == state["generation_grants"]["eval-v4-01"]["grant_sha256"]
    assert prepared.reservation_sha256 == state["provider_budget_reservations"]["eval-v4-01:generation"]["reservation_sha256"]
    assert prepared.timeout_seconds == 12


def test_durable_dispatch_immediately_precedes_synthetic_entry_and_secret_is_not_durable(tmp_path):
    store, _ = prepared_store(tmp_path); boundary = SyntheticBoundary(store, {CREDENTIAL: FAKE})
    assert boundary.execute_preflight() == {"input_tokens": 2852}
    assert boundary.calls == 1
    state = store.load(); history = store._read_journal()
    assert state["counters"]["token_preflights_consumed"] == 1
    assert history["events"][-1]["operation"] == "preflight_result_validated"
    assert FAKE not in json.dumps(state) and FAKE not in json.dumps(history)
    with pytest.raises((AggregateStateError, ExecutionBoundaryError)):
        boundary.execute_preflight()
    assert boundary.calls == 1


@pytest.mark.parametrize("failure", [TimeoutError("synthetic timeout"), RuntimeError("synthetic provider error")])
def test_provider_failure_after_durable_dispatch_remains_consumed(tmp_path, failure):
    store, _ = prepared_store(tmp_path); boundary = SyntheticBoundary(store, {CREDENTIAL: FAKE}, fail=failure)
    with pytest.raises(type(failure), match="synthetic"):
        boundary.execute_preflight()
    state = store.load()
    assert boundary.calls == 1
    assert state["counters"]["token_preflights_consumed"] == 1
    assert state["counters"]["retries"] == 0
    with pytest.raises(AggregateStateError): store.release_expired_preflight_budget()


def test_local_client_failure_and_dispatch_persistence_failure_never_enter_provider(tmp_path):
    store, _ = prepared_store(tmp_path)
    class LocalFailure(SyntheticBoundary):
        def _prepare_client(self, prepared): raise ValueError("local preparation")
    boundary = LocalFailure(store, {CREDENTIAL: FAKE})
    with pytest.raises(ValueError, match="local preparation"): boundary.execute_preflight()
    assert boundary.calls == 0 and store.load()["counters"]["token_preflights_reserved"] == 1
    def fail(point):
        if point == "before_history_replace": raise RuntimeError("persistence")
    failing = SyntheticBoundary(AggregateStore(store.root, store.clock, fail), {CREDENTIAL: FAKE})
    with pytest.raises(RuntimeError, match="persistence"): failing.execute_preflight()
    assert failing.calls == 0
    recovered = AggregateStore(store.root, store.clock).load()
    assert recovered["counters"]["token_preflights_reserved"] == 1
    assert recovered["counters"]["token_preflights_consumed"] == 0


def test_final_revalidation_rejects_expiry_after_client_preparation(tmp_path):
    store, clock = prepared_store(tmp_path)
    class Expire(SyntheticBoundary):
        def _prepare_client(self, prepared):
            client = super()._prepare_client(prepared)
            clock.now += timedelta(minutes=16)
            return client
    boundary = Expire(store, {CREDENTIAL: FAKE})
    with pytest.raises((AggregateStateError, ExecutionBoundaryError)):
        boundary.execute_preflight()
    assert boundary.calls == 0
    assert all(e["operation"] != "provider_dispatch_started" for e in store._read_journal()["events"])


def _execute_with_post_client_mutation(store, mutate):
    class Mutate(SyntheticBoundary):
        def _prepare_client(self, prepared):
            client = super()._prepare_client(prepared)
            mutate()
            return client
    boundary = Mutate(store, {CREDENTIAL: FAKE})
    return boundary


def test_final_revalidation_isolates_grant_expiry(tmp_path):
    store, clock = prepared_store(tmp_path)
    boundary = _execute_with_post_client_mutation(
        store, lambda: setattr(clock, "now", clock.now + timedelta(minutes=16)))
    with pytest.raises(ExecutionBoundaryError, match="active preflight authority is unavailable"):
        boundary.execute_preflight()
    assert boundary.calls == 0
    assert not any(e["operation"] == "provider_dispatch_started" for e in store._read_journal()["events"])


def test_final_revalidation_isolates_aggregate_expiry(tmp_path):
    from test_v4_formal_evaluation_live_generation import Clock
    from v4_formal_evaluation_live_deterministic import resolve_deterministic_cases
    clock = Clock(); store = AggregateStore(tmp_path / "state", clock)
    store.initialize("Operator", "Reviewer"); store.resume("Reviewer")
    clock.now += timedelta(days=6, hours=23, minutes=50)
    resolve_deterministic_cases(store); store.bind_ai_case_envelopes()
    store.prepare_preflight_grant(); store.authorize_preflight_budget()
    boundary = _execute_with_post_client_mutation(
        store, lambda: setattr(clock, "now", clock.now + timedelta(minutes=11)))
    with pytest.raises(ExecutionBoundaryError, match="aggregate expired before provider entry"):
        boundary.execute_preflight()
    assert boundary.calls == 0
    assert not any(e["operation"] == "provider_dispatch_started" for e in store._read_journal()["events"])


def test_final_revalidation_isolates_released_reservation(tmp_path):
    store, clock = prepared_store(tmp_path); original = clock.now
    def release_then_rewind():
        clock.now += timedelta(minutes=16)
        store.release_expired_preflight_budget()
        clock.now = original
    boundary = _execute_with_post_client_mutation(store, release_then_rewind)
    with pytest.raises(ExecutionBoundaryError, match="provider reservation was released"):
        boundary.execute_preflight()
    assert boundary.calls == 0
    assert not any(e["operation"] == "provider_dispatch_started" for e in store._read_journal()["events"])


def test_final_revalidation_isolates_concurrent_consumption(tmp_path):
    store, _ = prepared_store(tmp_path)
    boundary = _execute_with_post_client_mutation(store, store.record_provider_dispatch_started)
    with pytest.raises(ExecutionBoundaryError, match="provider attempt is already consumed"):
        boundary.execute_preflight()
    assert boundary.calls == 0
    dispatches = [e for e in store._read_journal()["events"] if e["operation"] == "provider_dispatch_started"]
    assert len(dispatches) == 1


def test_fixed_launchers_are_secret_safe_and_coordination_cli_unchanged():
    root = Path(__file__).parent
    preflight = (root / "run_v4_formal_evaluation_live_preflight_operator.zsh").read_text()
    generation = (root / "run_v4_formal_evaluation_live_generation_operator.zsh").read_text()
    assert preflight.startswith("#!/usr/bin/env zsh") and "read -p" not in preflight
    assert 'ZSH_EVAL_CONTEXT:-' in preflight and 'ZSH_EVAL_CONTEXT:-' in generation
    assert 'read -s "GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY?OpenAI evaluation key: "' in preflight
    assert "set +x" in preflight and "trap cleanup_m8_credential EXIT" in preflight
    for signal, code in (("INT", "130"), ("TERM", "143"), ("HUP", "129")):
        assert f"trap 'handle_m8_signal {signal} {code}' {signal}" in preflight
    assert "boundary_docker.sh execute $" not in preflight
    assert "read -s" not in generation  # generation fails before prompting.
    cli = (root / "v4_formal_evaluation_live_cli.py").read_text()
    namespace = {}; exec(compile(cli.split("def parser", 1)[0], "cli", "exec"), namespace)
    assert len(namespace["PUBLIC_COMMANDS"]) == 10 and not any("generation" in x for x in namespace["PUBLIC_COMMANDS"])
    assert "generation_dispatch_started" not in (root / "v4_formal_evaluation_live_state.py").read_text()


def test_pinned_sdk_retry_timeout_and_production_synthetic_isolation():
    source = Path(__file__).with_name("v4_formal_evaluation_live_execution.py").read_text()
    assert SDK_PIN == "openai==2.45.0"
    assert "automatic_retries\"] != 0" in source
    assert "token_preflight_timeout_seconds" in source and "generation_timeout_seconds" in source
    assert "SyntheticBoundary" not in source and FAKE not in source
    assert "SyntheticBoundary" not in source and FAKE not in source
    factory = Path(__file__).with_name("openai_client_factory.py").read_text()
    assert "max_retries=0" in factory and "trust_env=False" in factory


def test_actual_boundary_uses_canonical_zero_retry_client_factory(tmp_path):
    store, _ = prepared_store(tmp_path)
    boundary = SyntheticBoundary(store, {CREDENTIAL: FAKE})
    prepared = boundary.precheck("preflight")
    client = boundary._prepare_client(prepared)
    assert client.client.arguments["max_retries"] == 0
    assert client.client.arguments["base_url"] == "https://api.openai.com/v1"
    assert client._http_client.arguments == {"trust_env": False}
    assert prepared.request_configuration["automatic_retries"] == 0
    assert prepared.timeout_seconds == 5
    assert boundary.calls == 0
    client.close()


def test_launcher_exit_code_and_signal_contracts_are_exact():
    text = Path(__file__).with_name("run_v4_formal_evaluation_live_preflight_operator.zsh").read_text()
    assert "local child_exit_code=$?" in text
    assert "return $child_exit_code" in text
    assert "trap - EXIT INT TERM HUP" in text
    assert "trap 'handle_m8_signal INT 130' INT" in text
    assert "trap 'handle_m8_signal TERM 143' TERM" in text
    assert "trap 'handle_m8_signal HUP 129' HUP" in text


def _prepared_real_time_store(root):
    from v4_formal_evaluation_live_deterministic import resolve_deterministic_cases
    store = AggregateStore(root)
    store.initialize("Operator", "Reviewer"); store.resume("Reviewer")
    resolve_deterministic_cases(store); store.bind_ai_case_envelopes()
    store.prepare_preflight_grant(); store.authorize_preflight_budget()
    return store


def _write_fake_docker_and_hook(tmp_path, synthetic=True):
    repo = Path(__file__).parents[3]
    fake_bin = tmp_path / "bin"; fake_bin.mkdir(parents=True)
    docker = fake_bin / "docker"
    docker.write_text(textwrap.dedent("""\
        #!/usr/bin/env python3
        import json, os, subprocess, sys
        from pathlib import Path
        args = sys.argv[1:]
        log = Path(os.environ["M8_DOCKER_ARGV_LOG"])
        with log.open("a") as stream: stream.write(json.dumps(args) + "\\n")
        secret = os.environ.get("GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY", "")
        if secret and secret in "\\0".join(args): raise SystemExit(91)
        child_env = dict(os.environ)
        image = "gotime-moving-service-stage-b:openai-2.45.0"
        index = args.index(image)
        for position, item in enumerate(args[:index]):
            if item == "--env":
                value = args[position + 1]
                if "=" in value:
                    name, env_value = value.split("=", 1)
                    child_env[name] = env_value.replace("/workspace", os.environ["M8_REPO"])
                elif value in os.environ: child_env[value] = os.environ[value]
        command = args[index + 1:]
        if image != "gotime-moving-service-stage-b:openai-2.45.0": raise SystemExit(92)
        if command[0] != "python": raise SystemExit(93)
        mode = os.environ.get("M8_FAKE_DOCKER_EXECUTION", "")
        if command[-1] == "execute" and mode == "exit47": raise SystemExit(47)
        if command[-1] == "execute" and mode == "wait-for-signal":
            import time
            time.sleep(30)
        command[0] = sys.executable
        command[1] = command[1].replace("/workspace", os.environ["M8_REPO"])
        child_env["PYTHONPATH"] = os.environ["M8_HOOK_DIR"] + os.pathsep + child_env.get("PYTHONPATH", "")
        completed = subprocess.run(command, cwd=os.environ["M8_REPO"], env=child_env)
        raise SystemExit(completed.returncode)
    """))
    docker.chmod(docker.stat().st_mode | stat.S_IXUSR)
    hook = tmp_path / "hook"; hook.mkdir()
    synthetic_patch = "" if not synthetic else textwrap.dedent("""\
        execution.ProviderExecutionBoundary._live_readiness_authorized = lambda self, phase, current: True
        execution.ProviderExecutionBoundary._client_constructors = lambda self: (Client, Http)
        def enter(self, prepared, owned):
            current=self.store.load()
            assert current["provider_budget_reservations"][prepared.case_id]["lifecycle"]["status"] == "consumed"
            assert owned.client.arguments["max_retries"] == 0
            assert owned._http_client.arguments == {"trust_env": False}
            Path(os.environ["M8_PROVIDER_MARKER"]).write_text("synthetic-entry=1\\n")
            if prepared.phase == "generation":
                from v4_formal_evaluation_runner import valid_synthetic_response
                return valid_synthetic_response(prepared.case_id)
            return {"input_tokens": 2852}
        execution.ProviderExecutionBoundary._enter_provider = enter
    """)
    (hook / "sitecustomize.py").write_text(textwrap.dedent("""\
        import os
        from pathlib import Path
        import v4_formal_evaluation_live_state as state
        state.default_root = lambda: Path(os.environ["M8_STATE"])
        import v4_formal_evaluation_live_execution as execution
        class Http:
            def __init__(self, **kwargs): self.arguments=kwargs
            def close(self): pass
        class Client:
            def __init__(self, **kwargs): self.arguments=kwargs; self.max_retries=kwargs["max_retries"]
            def close(self): pass
    """) + synthetic_patch)
    return fake_bin, hook


def _actual_launcher_environment(tmp_path, store, synthetic=True):
    fake_bin, hook = _write_fake_docker_and_hook(tmp_path, synthetic)
    repo = Path(__file__).parents[3]
    return dict(
        os.environ,
        PATH=f"{fake_bin}:{os.environ['PATH']}",
        M8_REPO=str(repo), M8_STATE=str(store.root), M8_HOOK_DIR=str(hook),
        M8_DOCKER_ARGV_LOG=str(tmp_path / "docker-argv.jsonl"),
        M8_PROVIDER_MARKER=str(tmp_path / "provider-marker.txt"),
    )


def test_exact_unchanged_operator_launcher_rehearses_real_docker_wrapper_with_xtrace(tmp_path):
    if shutil.which("zsh") is None:
        pytest.skip("zsh is required for the exact operator-launcher rehearsal")
    store = _prepared_real_time_store(tmp_path / "aggregate")
    environment = _actual_launcher_environment(tmp_path, store)
    launcher = Path(__file__).with_name("run_v4_formal_evaluation_live_preflight_operator.zsh")
    result = subprocess.run(
        ["zsh", "-x", str(launcher)], cwd=Path(__file__).parents[3], env=environment,
        input=FAKE + "\n", text=True, capture_output=True, timeout=30,
    )
    assert result.returncode == 0
    assert FAKE not in result.stdout + result.stderr
    assert (tmp_path / "provider-marker.txt").read_text() == "synthetic-entry=1\n"
    invocations = [json.loads(line) for line in (tmp_path / "docker-argv.jsonl").read_text().splitlines()]
    assert len(invocations) == 2
    assert all(FAKE not in "\0".join(argv) for argv in invocations)
    assert invocations[-1].count("GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY") == 1
    assert all("gotime-moving-service-stage-b:openai-2.45.0" in argv for argv in invocations)
    state = store.load()
    durable = json.dumps(state) + json.dumps(store._read_journal())
    assert FAKE not in durable
    assert state["counters"]["token_preflights_consumed"] == 1
    assert state["preflight_results"]["eval-v4-01"]["immutable_binding"]["input_tokens"] == 2852
    assert state["preflight_evidence"]["eval-v4-01"]["immutable_binding"]["generation_gate_binding_eligible"] is False
    assert state["reviewed_preflight_evidence"] == {}
    for path in tmp_path.rglob("*"):
        if path.is_file() and path.name != "sitecustomize.py":
            assert FAKE not in path.read_text(errors="ignore"), path


def test_actual_production_preflight_launcher_fails_before_credential_prompt(tmp_path):
    if shutil.which("zsh") is None:
        pytest.skip("zsh is required for production launcher rehearsal")
    store = _prepared_real_time_store(tmp_path / "aggregate")
    environment = _actual_launcher_environment(tmp_path, store, synthetic=False)
    launcher = Path(__file__).with_name("run_v4_formal_evaluation_live_preflight_operator.zsh")
    result = subprocess.run(
        ["zsh", str(launcher)], cwd=Path(__file__).parents[3], env=environment,
        text=True, capture_output=True, timeout=30,
    )
    assert result.returncode != 0
    assert "OpenAI evaluation key" not in result.stdout + result.stderr
    assert not (tmp_path / "provider-marker.txt").exists()
    assert not any(e["operation"] == "provider_dispatch_started" for e in store._read_journal()["events"])


def test_both_operator_launchers_refuse_sourcing_without_caller_side_effects(tmp_path):
    if shutil.which("zsh") is None:
        pytest.skip("zsh is required for sourced-launcher tests")
    repo = Path(__file__).parents[3]
    for name in ("run_v4_formal_evaluation_live_preflight_operator.zsh",
                 "run_v4_formal_evaluation_live_generation_operator.zsh"):
        launcher = Path(__file__).with_name(name)
        command = (
            "setopt xtrace; [[ -o xtrace ]] && before=on || before=off; "
            "before_traps=$(trap); "
            f"source {launcher}; rc=$?; "
            "[[ -o xtrace ]] && after=on || after=off; "
            "after_traps=$(trap); [[ $before_traps == $after_traps ]] && traps=same || traps=changed; "
            "print -r -- caller-alive:$rc:$before:$after:$traps:${GOTIME_MOVING_SERVICE_EVAL_OPENAI_API_KEY-unset}"
        )
        result = subprocess.run(["zsh", "-c", command], cwd=repo, text=True, capture_output=True)
        assert result.returncode == 0
        assert "caller-alive:2:on:on:same:unset" in result.stdout
        assert "OpenAI evaluation key" not in result.stdout + result.stderr


def test_actual_generation_launcher_fails_before_prompt_and_provider_entry(tmp_path):
    if shutil.which("zsh") is None:
        pytest.skip("zsh is required for generation launcher rehearsal")
    store = _prepared_real_time_store(tmp_path / "aggregate")
    environment = _actual_launcher_environment(tmp_path, store)
    launcher = Path(__file__).with_name("run_v4_formal_evaluation_live_generation_operator.zsh")
    result = subprocess.run(
        ["zsh", "-x", str(launcher)], cwd=Path(__file__).parents[3], env=environment,
        text=True, capture_output=True, timeout=30,
    )
    assert result.returncode != 0
    assert "OpenAI evaluation key" not in result.stdout + result.stderr
    assert not (tmp_path / "provider-marker.txt").exists()
    invocations = [json.loads(line) for line in (tmp_path / "docker-argv.jsonl").read_text().splitlines()]
    assert len(invocations) == 1
    assert "run_v4_formal_evaluation_live_generation_boundary_docker.sh" not in "\0".join(invocations[0])
    assert invocations[0][-1] == "scripts/experiments/suggest_moving_service_questions/v4_formal_evaluation_live_generation_entry.py"


def test_operator_launcher_preserves_child_exit_and_signal_codes(tmp_path):
    if shutil.which("zsh") is None:
        pytest.skip("zsh is required for launcher signal tests")
    repo = Path(__file__).parents[3]
    launcher = Path(__file__).with_name("run_v4_formal_evaluation_live_preflight_operator.zsh")
    store = _prepared_real_time_store(tmp_path / "exit-state")
    environment = dict(_actual_launcher_environment(tmp_path / "exit", store),
                       M8_FAKE_DOCKER_EXECUTION="exit47")
    result = subprocess.run(["zsh", str(launcher)], cwd=repo, env=environment, input=FAKE + "\n",
                            text=True, capture_output=True, timeout=10)
    assert result.returncode == 47 and FAKE not in result.stdout + result.stderr
    assert all(FAKE not in path.read_text(errors="ignore") for path in (tmp_path / "exit").rglob("*") if path.is_file())
    def reset_signals():
        for item in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            signal.signal(item, signal.SIG_DFL)
    for sig, expected in ((signal.SIGINT, 130), (signal.SIGTERM, 143), (signal.SIGHUP, 129)):
        signal_root = tmp_path / f"signal-{sig}"
        store = _prepared_real_time_store(signal_root / "state")
        environment = dict(_actual_launcher_environment(signal_root, store),
                           M8_FAKE_DOCKER_EXECUTION="wait-for-signal")
        process = subprocess.Popen(["zsh", str(launcher)], cwd=repo, env=environment, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                   start_new_session=True, preexec_fn=reset_signals)
        process.stdin.write(FAKE + "\n"); process.stdin.flush()
        import time; time.sleep(0.2); os.killpg(process.pid, sig)
        stdout, stderr = process.communicate(timeout=5)
        assert process.returncode == expected and FAKE not in stdout + stderr
        assert all(FAKE not in path.read_text(errors="ignore") for path in signal_root.rglob("*") if path.is_file())
