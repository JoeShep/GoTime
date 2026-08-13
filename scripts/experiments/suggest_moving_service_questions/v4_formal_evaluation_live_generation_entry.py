#!/usr/bin/env python3
"""Fixed production generation readiness entry; evidence/live authorization absent."""
from v4_formal_evaluation_live_execution import ProviderExecutionBoundary
from v4_formal_evaluation_live_state import AggregateStore

ProviderExecutionBoundary(AggregateStore()).precheck("generation")
