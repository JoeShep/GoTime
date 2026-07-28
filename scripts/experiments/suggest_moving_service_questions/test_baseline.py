#!/usr/bin/env python3
"""Compatibility tests for the runtime-aligned v1 artifact package."""

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evaluate_baseline as artifacts


class ArtifactCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.artifacts = artifacts.load_artifacts()

    def assert_rejected(self, mutate):
        changed = copy.deepcopy(self.artifacts)
        mutate(changed)
        with self.assertRaises(artifacts.ArtifactValidationError):
            artifacts.validate_artifacts(changed)

    def test_package_is_runtime_compatible(self):
        result = artifacts.validate_artifacts(self.artifacts)

        self.assertEqual(1, result["knowledge_item_count"])
        self.assertEqual(3, len(result["request_fixtures"]))
        self.assertEqual(10, len(result["response_results"]))
        self.assertEqual(7, len(result["execution_results"]))

    def test_manifest_separates_contract_and_real_model_readiness(self):
        manifest = self.artifacts["manifest"]

        self.assertTrue(manifest["contract_test_eligible"])
        self.assertEqual([], manifest["contract_test_ineligibility_reasons"])
        self.assertFalse(manifest["real_model_evaluation_eligible"])
        self.assertGreater(
            len(manifest["real_model_ineligibility_reasons"]), 0
        )

    def test_false_readiness_requires_a_reason(self):
        self.assert_rejected(
            lambda package: package["manifest"].update(
                contract_test_eligible=False,
                contract_test_ineligibility_reasons=[],
            )
        )

    def test_true_readiness_cannot_retain_ineligibility_reasons(self):
        self.assert_rejected(
            lambda package: package["manifest"].update(
                contract_test_ineligibility_reasons=["stale reason"]
            )
        )

    def test_runtime_version_drift_is_rejected(self):
        self.assert_rejected(
            lambda package: package["manifest"].update(
                schema_version="obsolete-schema"
            )
        )

    def test_knowledge_drift_is_rejected(self):
        self.assert_rejected(
            lambda package: package["knowledge"]["items"][0].update(
                statement="A different statement."
            )
        )

    def test_fallback_order_drift_is_rejected(self):
        self.assert_rejected(
            lambda package: package["baseline"]["questions"][0].update(
                priority=999
            )
        )

    def test_request_fixture_drift_is_rejected(self):
        self.assert_rejected(
            lambda package: package["scenarios"]["scenarios"][0][
                "expected_missing_categories"
            ].clear()
        )

    def test_response_cases_use_runtime_validation(self):
        result = artifacts.validate_artifacts(self.artifacts)
        outcomes = {
            item["response_fixture_id"]: item
            for item in result["response_results"]
        }

        self.assertTrue(outcomes["valid_storage_suggestion"]["valid"])
        self.assertTrue(outcomes["valid_zero_suggestions"]["valid"])
        for fixture_id, outcome in outcomes.items():
            if fixture_id.startswith("invalid_"):
                self.assertFalse(outcome["valid"])
                self.assertEqual(
                    "fallback-temporary-storage-v1",
                    outcome["fallback_question_id"],
                )

    def test_invalid_response_expectation_drift_is_rejected(self):
        self.assert_rejected(
            lambda package: package["responses"]["cases"][2].update(
                expected_valid=True
            )
        )

    def test_execution_expectation_drift_is_rejected(self):
        self.assert_rejected(
            lambda package: package["expected"]["execution_cases"][0].update(
                expected_source="none"
            )
        )

    def test_knowledge_remains_explicitly_unapproved(self):
        knowledge = self.artifacts["knowledge"]

        self.assertEqual("implementation_fixture", knowledge["status"])
        self.assertFalse(knowledge["real_model_grounding_approved"])
        self.assertIn(
            "fake_adapter_testing",
            knowledge["valid_for"],
        )
        self.assertTrue(knowledge["limitations"])


if __name__ == "__main__":
    unittest.main()
