#!/usr/bin/env python3
"""Validate and evaluate the fixed deterministic experiment baseline."""

import argparse
import json
from pathlib import Path

STATUSES = {"known", "unknown", "not_applicable", "not_supplied"}
FILES = {
    "manifest": "manifest.json",
    "knowledge": "curated-knowledge.json",
    "baseline": "deterministic-baseline.json",
    "scenarios": "scenarios.json",
    "expected": "expected-results.json",
}


class ArtifactValidationError(ValueError):
    pass


def _fail(message):
    raise ArtifactValidationError(message)


def _require(obj, fields, context):
    if not isinstance(obj, dict):
        _fail(f"{context}: must be an object")
    missing = [field for field in fields if field not in obj]
    if missing:
        _fail(f"{context}: missing required fields: {', '.join(missing)}")


def _expect(value, expected_type, context):
    if not isinstance(value, expected_type):
        _fail(f"{context}: expected {expected_type.__name__}")


def default_artifact_dir():
    return Path(__file__).resolve().parents[3] / "docs/experiments/suggest-moving-service-questions/v1"


def load_artifacts(directory=None):
    root = Path(directory or default_artifact_dir())
    return {name: json.loads((root / filename).read_text()) for name, filename in FILES.items()}


def validate_artifacts(artifacts):
    manifest = artifacts["manifest"]
    knowledge = artifacts["knowledge"]
    baseline = artifacts["baseline"]
    scenarios_doc = artifacts["scenarios"]
    expected_doc = artifacts["expected"]
    _require(manifest, ["experiment", "artifact_version", "knowledge_version", "baseline_version",
                        "scenario_version", "expectations_version", "status",
                        "ai_evaluation_eligible"], "manifest")
    if manifest["experiment"] != "suggest_moving_service_questions":
        _fail("manifest: unexpected experiment")
    if manifest["status"] not in {"draft", "frozen"}:
        _fail("manifest: status must be draft or frozen")
    _expect(manifest["ai_evaluation_eligible"], bool, "manifest ai_evaluation_eligible")
    if manifest["status"] == "draft" and manifest["ai_evaluation_eligible"] is not False:
        _fail("manifest: draft artifacts cannot be AI-evaluation eligible")
    versions = [
        ("knowledge", "fixture_version", "knowledge_version"),
        ("baseline", "baseline_version", "baseline_version"),
        ("scenarios", "scenario_version", "scenario_version"),
        ("expected", "expectations_version", "expectations_version"),
    ]
    for artifact_name, field, manifest_field in versions:
        if artifacts[artifact_name].get(field) != manifest[manifest_field]:
            _fail(f"{artifact_name}: version is incompatible with manifest")

    _require(knowledge, ["fixture_version", "status", "reviewed_at", "sources", "items"], "knowledge")
    _expect(knowledge["sources"], list, "knowledge sources")
    _expect(knowledge["items"], list, "knowledge items")
    knowledge_ids, claim_ids = set(), set()
    source_ids = {source.get("source_id") for source in knowledge["sources"]}
    for item in knowledge["items"]:
        _require(item, ["knowledge_id", "service_model", "description", "relevant_circumstances",
                        "typical_tradeoffs", "information_needed_to_evaluate_fit", "claims",
                        "reviewed_at", "freshness_guidance", "version"], "knowledge item")
        kid = item["knowledge_id"]
        _expect(kid, str, "knowledge_id")
        for field in ("relevant_circumstances", "typical_tradeoffs",
                      "information_needed_to_evaluate_fit", "claims"):
            _expect(item[field], list, f"knowledge item {kid} {field}")
        if kid in knowledge_ids:
            _fail(f"knowledge: duplicate knowledge_id {kid}")
        knowledge_ids.add(kid)
        for claim in item["claims"]:
            _require(claim, ["claim_id", "target_field", "claim_requirement", "statement",
                             "verification_status", "source_ids", "review_notes"], f"claim in {kid}")
            cid = claim["claim_id"]
            _expect(cid, str, f"claim in {kid} claim_id")
            _expect(claim["source_ids"], list, f"claim {cid} source_ids")
            if cid in claim_ids:
                _fail(f"knowledge: duplicate claim_id {cid}")
            claim_ids.add(cid)
            if claim["verification_status"] not in {"unverified", "verified"}:
                _fail(f"claim {cid}: invalid verification_status")
            if not set(claim["source_ids"]).issubset(source_ids):
                _fail(f"claim {cid}: unknown source reference")
            if claim["verification_status"] == "verified" and (
                    not claim["statement"] or not claim["source_ids"]):
                _fail(f"claim {cid}: verified claims require a statement and source")

    _require(baseline, ["baseline_version", "status", "decision_id",
                        "supported_move_types", "questions"], "baseline")
    _expect(baseline["supported_move_types"], list, "baseline supported_move_types")
    _expect(baseline["questions"], list, "baseline questions")
    question_ids, question_categories, questions_by_id = set(), set(), {}
    priorities = set()
    for question in baseline["questions"]:
        _require(question, ["question_id", "priority", "information_category", "question",
                            "deterministic_rationale", "relevant_knowledge_ids",
                            "relevant_claim_ids"], "baseline question")
        qid = question["question_id"]
        _expect(question["priority"], int, f"question {qid} priority")
        for field in ("relevant_knowledge_ids", "relevant_claim_ids"):
            _expect(question[field], list, f"question {qid} {field}")
        if qid in question_ids or question["priority"] in priorities:
            _fail("baseline: question IDs and priorities must be unique")
        question_ids.add(qid)
        questions_by_id[qid] = question
        priorities.add(question["priority"])
        question_categories.add(question["information_category"])
        if not set(question["relevant_knowledge_ids"]).issubset(knowledge_ids):
            _fail(f"question {qid}: unknown knowledge reference")
        if not set(question["relevant_claim_ids"]).issubset(claim_ids):
            _fail(f"question {qid}: unknown claim reference")

    _require(scenarios_doc, ["scenario_version", "status", "information_categories",
                             "scenarios"], "scenarios")
    _expect(scenarios_doc["information_categories"], list, "scenario information_categories")
    _expect(scenarios_doc["scenarios"], list, "scenarios")
    categories = set(scenarios_doc["information_categories"])
    if not question_categories.issubset(categories):
        _fail("scenarios: baseline question category is not declared")
    scenario_ids = set()
    for scenario in scenarios_doc["scenarios"]:
        _require(scenario, ["scenario_id", "label", "trusted_state", "missing_information",
                            "inapplicable_information", "prohibited_question_categories",
                            "known_constraints", "open_decision", "existing_recommendation",
                            "curated_knowledge_ids"], "scenario")
        sid = scenario["scenario_id"]
        _expect(scenario["trusted_state"], dict, f"scenario {sid} trusted_state")
        for field in ("missing_information", "inapplicable_information",
                      "prohibited_question_categories", "known_constraints",
                      "curated_knowledge_ids"):
            _expect(scenario[field], list, f"scenario {sid} {field}")
        if sid in scenario_ids:
            _fail(f"scenarios: duplicate scenario_id {sid}")
        scenario_ids.add(sid)
        state = scenario["trusted_state"]
        for field, entry in state.items():
            _require(entry, ["status"], f"scenario {sid} state {field}")
            status = entry["status"]
            if status not in STATUSES:
                _fail(f"scenario {sid} state {field}: invalid status")
            if status == "known" and ("value" not in entry or entry["value"] is None):
                _fail(f"scenario {sid} state {field}: known requires a value")
            if status != "known" and "value" in entry:
                _fail(f"scenario {sid} state {field}: only known may contain a value")
        missing = set(scenario["missing_information"])
        inapplicable = set(scenario["inapplicable_information"])
        prohibited = set(scenario["prohibited_question_categories"])
        if not (missing | inapplicable | prohibited).issubset(categories):
            _fail(f"scenario {sid}: unknown information category reference")
        if missing & inapplicable:
            _fail(f"scenario {sid}: information cannot be both missing and inapplicable")
        for category in categories & set(state):
            status = state[category]["status"]
            if (category in missing) != (status == "unknown"):
                _fail(f"scenario {sid}: missing_information contradicts {category} status")
            if (category in inapplicable) != (status == "not_applicable"):
                _fail(f"scenario {sid}: inapplicable_information contradicts {category} status")
        if missing & prohibited:
            _fail(f"scenario {sid}: a missing category cannot also be prohibited")
        if scenario["open_decision"] != {"decision_id": baseline["decision_id"], "status": "unresolved"}:
            _fail(f"scenario {sid}: open decision is incompatible with baseline")
        if not set(scenario["curated_knowledge_ids"]).issubset(knowledge_ids):
            _fail(f"scenario {sid}: unknown knowledge reference")

    _require(expected_doc, ["expectations_version", "status", "results"], "expected results")
    _expect(expected_doc["results"], list, "expected results")
    expected_ids = set()
    for result in expected_doc["results"]:
        _require(result, ["scenario_id", "expected_question_id", "expected_information_category",
                          "acceptable_question_themes", "zero_suggestions_allowed"],
                 "expected result")
        sid = result["scenario_id"]
        _expect(result["acceptable_question_themes"], list,
                f"expected result {sid} acceptable_question_themes")
        _expect(result["zero_suggestions_allowed"], bool,
                f"expected result {sid} zero_suggestions_allowed")
        expected_ids.add(sid)
        if sid not in scenario_ids:
            _fail(f"expected result: unknown scenario {sid}")
        qid = result["expected_question_id"]
        if qid is not None and qid not in question_ids:
            _fail(f"expected result {sid}: unknown question reference")
        if (qid is None) != (result["expected_information_category"] is None):
            _fail(f"expected result {sid}: question and category must both be set or null")
        if qid is not None and (
                questions_by_id[qid]["information_category"]
                != result["expected_information_category"]):
            _fail(f"expected result {sid}: question category is inconsistent")
    if expected_ids != scenario_ids or len(expected_ids) != len(expected_doc["results"]):
        _fail("expected results: must contain exactly one result per scenario")
    return artifacts


def evaluate_scenario(artifacts, scenario_id):
    validate_artifacts(artifacts)
    manifest, baseline = artifacts["manifest"], artifacts["baseline"]
    scenario = next((item for item in artifacts["scenarios"]["scenarios"]
                     if item["scenario_id"] == scenario_id), None)
    if scenario is None:
        _fail(f"unknown scenario {scenario_id}")
    known = {field: entry["value"] for field, entry in scenario["trusted_state"].items()
             if entry["status"] == "known"}
    available = set(scenario["curated_knowledge_ids"])
    candidates = [
        question for question in baseline["questions"]
        if question["information_category"] in scenario["missing_information"]
        and question["information_category"] not in scenario["inapplicable_information"]
        and question["information_category"] not in scenario["prohibited_question_categories"]
        and set(question["relevant_knowledge_ids"]).issubset(available)
    ]
    selected = min(candidates, key=lambda item: item["priority"]) if candidates else None
    return {
        "scenario_id": scenario_id,
        "artifact_status": manifest["status"],
        "ai_evaluation_eligible": manifest["ai_evaluation_eligible"],
        "baseline_version": baseline["baseline_version"],
        "contextual_known_facts": known,
        "question": None if selected is None else {
            key: selected[key] for key in
            ("question_id", "information_category", "question", "deterministic_rationale",
             "relevant_knowledge_ids", "relevant_claim_ids")
        },
        "no_question_reason": None if selected else
            "No applicable checklist question is grounded by the supplied knowledge."
    }


def evaluate_all(artifacts):
    results = [evaluate_scenario(artifacts, scenario["scenario_id"])
               for scenario in artifacts["scenarios"]["scenarios"]]
    expected = {item["scenario_id"]: item for item in artifacts["expected"]["results"]}
    for result in results:
        actual = result["question"]
        specification = expected[result["scenario_id"]]
        actual_id = actual["question_id"] if actual else None
        actual_category = actual["information_category"] if actual else None
        if actual_id != specification["expected_question_id"] or (
                actual_category != specification["expected_information_category"]):
            _fail(f"scenario {result['scenario_id']}: result does not match expectation")
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, default=default_artifact_dir())
    parser.add_argument("--scenario")
    args = parser.parse_args()
    artifacts = load_artifacts(args.artifacts)
    output = (evaluate_scenario(artifacts, args.scenario)
              if args.scenario else evaluate_all(artifacts))
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
