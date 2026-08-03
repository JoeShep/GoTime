"""Exact offline lifecycle CLI for the v2 follow-up pilot."""

from __future__ import annotations

import argparse

from v2_follow_up_lifecycle import (
    FALLBACK_COMPARISONS,
    finalize_v2_human_review,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status", required=True, choices=["approved", "rejected"])
    parser.add_argument("--grounding-supported", required=True, choices=["true", "false"])
    parser.add_argument("--invented-user-fact-present", required=True, choices=["true", "false"])
    parser.add_argument("--scope-overstatement-present", required=True, choices=["true", "false"])
    parser.add_argument("--provider-or-service-recommendation-present", required=True, choices=["true", "false"])
    parser.add_argument("--storage-required-claim-present", required=True, choices=["true", "false"])
    parser.add_argument("--clarity-score", required=True, type=int, choices=range(1, 6))
    parser.add_argument("--usefulness-score", required=True, type=int, choices=range(1, 6))
    parser.add_argument("--fallback-comparison", required=True, choices=sorted(FALLBACK_COMPARISONS))
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--notes", default="")
    args = parser.parse_args()
    boolean = lambda value: value == "true"
    finalize_v2_human_review(review={
        "human_review_status": args.status,
        "grounding_supported": boolean(args.grounding_supported),
        "invented_user_fact_present": boolean(args.invented_user_fact_present),
        "scope_overstatement_present": boolean(args.scope_overstatement_present),
        "provider_or_service_recommendation_present": boolean(args.provider_or_service_recommendation_present),
        "storage_required_claim_present": boolean(args.storage_required_claim_present),
        "clarity_score": args.clarity_score,
        "usefulness_score": args.usefulness_score,
        "fallback_comparison": args.fallback_comparison,
        "reviewer": args.reviewer,
        "bounded_review_notes": args.notes,
    })
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
