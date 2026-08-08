#!/usr/bin/env python3
"""
AgentK E2E Unified Test Runner Script
======================================
Executes end-to-end test suites across Tiers 1-4, verifying pass rates,
test collection counts, and generating clean execution reports.
"""

import sys
import os
import argparse

# Prepend project root to sys.path and set offline test environment variables
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("OPENAI_API_KEY", "mock-openai-key-for-e2e-testing")

import pytest


class ResultCollector:
    """Pytest plugin to collect test execution counts and results."""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.total = 0
        self.test_names = []

    def pytest_runtest_logreport(self, report):
        if report.when == "call":
            self.total += 1
            self.test_names.append((report.nodeid, report.outcome))
            if report.passed:
                self.passed += 1
            elif report.failed:
                self.failed += 1
            elif report.skipped:
                self.skipped += 1


def main():
    parser = argparse.ArgumentParser(description="AgentK Unified E2E Test Runner")
    parser.add_argument(
        "--tier",
        choices=["1", "2", "3", "4", "all"],
        default="all",
        help="Select E2E test tier to run: 1, 2, 3, 4, or all (default: all)"
    )
    args = parser.parse_args()

    tier_map = {
        "1": ("tier1", 35),
        "2": ("tier2", 35),
        "3": ("tier3", 10),
        "4": ("tier4", 5),
        "all": ("e2e", 85)
    }

    marker_name, min_expected_tests = tier_map[args.tier]

    print("================================================================================")
    print(f" AGENTK E2E TEST RUNNER - TIER: {args.tier.upper()} (Marker: '{marker_name}')")
    print("================================================================================")

    e2e_dir = os.path.join(PROJECT_ROOT, "tests", "e2e")
    pytest_args = [
        "-v",
        e2e_dir,
        "-m", marker_name
    ]

    collector = ResultCollector()
    exit_code = pytest.main(pytest_args, plugins=[collector])

    print("\n" + "=" * 80)
    print(" E2E TEST EXECUTION SUMMARY REPORT")
    print("=" * 80)
    print(f" Selected Tier         : {args.tier}")
    print(f" Target Marker         : {marker_name}")
    print(f" Total Tests Executed  : {collector.total}")
    print(f" Passed                : {collector.passed}")
    print(f" Failed                : {collector.failed}")
    print(f" Skipped               : {collector.skipped}")
    print(f" Pass Rate             : {(collector.passed / collector.total * 100) if collector.total > 0 else 0:.1f}%")
    print(f" Minimum Required Tests: {min_expected_tests}")
    print("=" * 80)

    # Verification checks
    if collector.total < min_expected_tests:
        print(f"❌ FAILURE: Test count ({collector.total}) is below required minimum ({min_expected_tests})!")
        sys.exit(1)

    if collector.failed > 0 or collector.passed != collector.total:
        print(f"❌ FAILURE: Pass rate is not 100%! ({collector.failed} failures detected)")
        sys.exit(1)

    print(f"✅ SUCCESS: All {collector.total} tests in Tier '{args.tier}' passed with 100% pass rate.")
    sys.exit(0)


if __name__ == "__main__":
    main()
