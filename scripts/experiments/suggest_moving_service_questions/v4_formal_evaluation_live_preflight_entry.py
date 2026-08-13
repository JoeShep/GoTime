#!/usr/bin/env python3
"""Fixed production preflight entry; closed until Milestone 18."""
import argparse
from v4_formal_evaluation_live_execution import ProviderExecutionBoundary
from v4_formal_evaluation_live_state import AggregateStore

parser = argparse.ArgumentParser()
parser.add_argument("mode", choices=("check", "execute"))
args = parser.parse_args()
boundary = ProviderExecutionBoundary(AggregateStore())
if args.mode == "check":
    boundary.precheck("preflight")
else:
    boundary.execute_preflight()
