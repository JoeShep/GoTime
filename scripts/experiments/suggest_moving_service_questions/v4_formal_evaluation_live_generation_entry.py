#!/usr/bin/env python3
"""Fixed generation execution entry; production live authorization remains absent."""
from v4_formal_evaluation_live_execution import ProviderExecutionBoundary
from v4_formal_evaluation_live_state import AggregateStore

ProviderExecutionBoundary(AggregateStore()).execute_generation()
