"""Offline-only review, deletion, and closure commands for the Stage B pilot."""

from __future__ import annotations

import argparse

from stage_b_lifecycle import (
    CLOSURE_REASONS,
    FALLBACK_COMPARISONS,
    REVIEW_STATUSES,
    close_stage_b_authorization,
    delete_stage_b_response_evidence,
    finalize_stage_b_human_review,
)


def _boolean(value: str) -> bool:
    if value == "true":
        return True
    if value == "false":
        return False
    raise argparse.ArgumentTypeError("value must be true or false")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage the one moving-service Stage B pilot lifecycle.")
    commands = parser.add_subparsers(dest="command", required=True)

    review = commands.add_parser("review", help="Finalize bounded human review and delete response evidence.")
    review.add_argument("--status", required=True, choices=sorted(REVIEW_STATUSES))
    review.add_argument("--grounding-supported", required=True, type=_boolean)
    review.add_argument("--invented-user-fact-present", required=True, type=_boolean)
    review.add_argument("--scope-overstatement-present", required=True, type=_boolean)
    review.add_argument("--provider-or-service-recommendation-present", required=True, type=_boolean)
    review.add_argument("--storage-required-claim-present", required=True, type=_boolean)
    review.add_argument("--clarity-score", required=True, type=int, choices=range(1, 6))
    review.add_argument("--usefulness-score", required=True, type=int, choices=range(1, 6))
    review.add_argument("--fallback-comparison", required=True, choices=sorted(FALLBACK_COMPARISONS))
    review.add_argument("--reviewer", required=True)
    review.add_argument("--notes", default="")

    delete = commands.add_parser("delete-expired-evidence", help="Delete evidence whose 30-day deadline has arrived.")
    delete.set_defaults(deletion_reason="retention_deadline", review_status="not_reviewed")

    close = commands.add_parser("close", help="Restore and verify permanent closed authorization.")
    close.add_argument("--reason", required=True, choices=sorted(CLOSURE_REASONS))
    return parser


def main() -> int:
    arguments = _parser().parse_args()
    if arguments.command == "review":
        finalize_stage_b_human_review(
            review={
                "human_review_status": arguments.status,
                "grounding_supported": arguments.grounding_supported,
                "invented_user_fact_present": arguments.invented_user_fact_present,
                "scope_overstatement_present": arguments.scope_overstatement_present,
                "provider_or_service_recommendation_present": arguments.provider_or_service_recommendation_present,
                "storage_required_claim_present": arguments.storage_required_claim_present,
                "clarity_score": arguments.clarity_score,
                "usefulness_score": arguments.usefulness_score,
                "fallback_comparison": arguments.fallback_comparison,
                "reviewer": arguments.reviewer,
                "bounded_review_notes": arguments.notes,
            }
        )
    elif arguments.command == "delete-expired-evidence":
        delete_stage_b_response_evidence(
            reason=arguments.deletion_reason,
            review_status=arguments.review_status,
        )
    else:
        close_stage_b_authorization(reason=arguments.reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
