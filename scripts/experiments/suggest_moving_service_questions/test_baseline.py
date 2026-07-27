#!/usr/bin/env python3
"""Tests for the fixed deterministic moving-service baseline."""

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evaluate_baseline as baseline


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.artifacts = baseline.load_artifacts()

    def assert_rejected(self, mutate):
        artifacts = copy.deepcopy(self.artifacts)
        mutate(artifacts)
        with self.assertRaises(baseline.ArtifactValidationError):
            baseline.validate_artifacts(artifacts)

    def test_artifacts_validate_and_match_all_expected_results(self):
        results = baseline.evaluate_all(self.artifacts)
        self.assertEqual(5, len(results))

    def test_returns_exactly_one_question_or_structured_none(self):
        results = baseline.evaluate_all(self.artifacts)
        for result in results:
            self.assertNotEqual(result["question"] is None, result["no_question_reason"] is None)

    def test_known_facts_are_preserved_without_repeat_questions(self):
        result = baseline.evaluate_scenario(self.artifacts, "storage-likely")
        self.assertEqual("possible", result["contextual_known_facts"]["temporary_storage_need"])
        self.assertFalse(result["contextual_known_facts"]["willing_to_drive_rental_truck"])
        self.assertNotIn(result["question"]["information_category"],
                         {"temporary_storage_need", "willing_to_drive_rental_truck"})

    def test_draft_status_blocks_ai_evaluation_and_claims_are_unverified(self):
        results = baseline.evaluate_all(self.artifacts)
        self.assertTrue(all(item["artifact_status"] == "draft" for item in results))
        self.assertTrue(all(item["ai_evaluation_eligible"] is False for item in results))
        claims = [claim for item in self.artifacts["knowledge"]["items"] for claim in item["claims"]]
        self.assertTrue(all(claim["verification_status"] == "unverified" for claim in claims))
        self.assertTrue(all(claim["statement"] is None and not claim["source_ids"] for claim in claims))

    def test_rejects_version_mismatch(self):
        self.assert_rejected(lambda a: a["baseline"].update(baseline_version="wrong"))

    def test_rejects_invalid_field_type(self):
        self.assert_rejected(lambda a: a["baseline"].update(questions="not-a-list"))

    def test_rejects_known_state_without_value(self):
        def mutate(a):
            del a["scenarios"]["scenarios"][0]["trusted_state"]["temporary_storage_need"]["value"]
        self.assert_rejected(mutate)

    def test_rejects_value_on_unknown_state(self):
        def mutate(a):
            a["scenarios"]["scenarios"][0]["trusted_state"]["packing_preference"]["value"] = "self_pack"
        self.assert_rejected(mutate)

    def test_rejects_known_category_listed_as_missing(self):
        def mutate(a):
            a["scenarios"]["scenarios"][0]["missing_information"].append("temporary_storage_need")
            a["scenarios"]["scenarios"][0]["prohibited_question_categories"].remove("temporary_storage_need")
        self.assert_rejected(mutate)

    def test_rejects_missing_and_inapplicable_contradiction(self):
        def mutate(a):
            a["scenarios"]["scenarios"][0]["inapplicable_information"].append("packing_preference")
        self.assert_rejected(mutate)

    def test_rejects_unknown_knowledge_and_claim_references(self):
        self.assert_rejected(lambda a: a["baseline"]["questions"][0]["relevant_knowledge_ids"].append("missing"))
        self.assert_rejected(lambda a: a["baseline"]["questions"][0]["relevant_claim_ids"].append("missing"))

    def test_rejects_inconsistent_expected_result(self):
        self.assert_rejected(
            lambda a: a["expected"]["results"][0].update(
                expected_question_id="moving-service-question.special-handling.v1"))


if __name__ == "__main__":
    unittest.main()
