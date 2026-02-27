"""
Main Test Runner for Giskard Tests
Runs all security and RAG evaluation tests
"""

import sys
from pathlib import Path
from typing import Dict, Any
import argparse
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tests.giskard.security_tests import GiskardSecurityTester
from tests.giskard.rag_evaluation import RAGEvaluator
from tests.giskard.config import RESULTS_DIR


def run_security_tests() -> Dict[str, Any]:
    """Run all security tests"""
    print("\n" + "🛡️ " * 40)
    print("SECURITY TESTING")
    print("🛡️ " * 40)

    tester = GiskardSecurityTester()
    summary = tester.run_all_tests()

    return summary


def run_rag_evaluation() -> Dict[str, Any]:
    """Run RAG evaluation tests"""
    print("\n" + "📊 " * 40)
    print("RAG EVALUATION")
    print("📊 " * 40)

    evaluator = RAGEvaluator()
    summary = evaluator.run_all_evaluations()

    return summary


def generate_report(security_summary: Dict[str, Any], rag_summary: Dict[str, Any]):
    """Generate comprehensive test report"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report = f"""
{"=" * 80}
MEDICAL RAG CHATBOT - COMPREHENSIVE TEST REPORT
{"=" * 80}

Generated: {timestamp}

{"=" * 80}
SECURITY TESTING RESULTS
{"=" * 80}

Total Tests: {security_summary["total_tests"]}
Passed: {security_summary["total_passed"]} ✅
Failed: {security_summary["total_failed"]} ❌
Pass Rate: {security_summary["pass_rate"]:.1f}%

Category Breakdown:
"""

    for category, results in security_summary["category_results"].items():
        pass_rate = (
            (results["passed"] / results["total_tests"] * 100)
            if results["total_tests"] > 0
            else 0
        )
        report += f"""
  {category.upper()}:
    Total: {results["total_tests"]}
    Passed: {results["passed"]} ✅
    Failed: {results["failed"]} ❌
    Pass Rate: {pass_rate:.1f}%
"""

    report += f"""
{"=" * 80}
RAG EVALUATION RESULTS
{"=" * 80}
"""

    for metric, results in rag_summary.items():
        total = results["total_questions"]
        passed = results["passed"]
        pass_rate = (passed / total * 100) if total > 0 else 0

        report += f"""
  {metric.upper()}:
    Total: {total}
    Passed: {passed} ✅
    Failed: {results["failed"]} ❌
    Pass Rate: {pass_rate:.1f}%
"""

    report += f"""
{"=" * 80}
RECOMMENDATIONS
{"=" * 80}
"""

    # Add recommendations based on results
    if security_summary["pass_rate"] < 80:
        report += """
⚠️ SECURITY: Pass rate below 80%. Review failed tests and strengthen guardrails.
"""
    else:
        report += """
✅ SECURITY: Good pass rate. Continue monitoring.
"""

    # Check specific categories
    for category, results in security_summary["category_results"].items():
        pass_rate = (
            (results["passed"] / results["total_tests"] * 100)
            if results["total_tests"] > 0
            else 0
        )
        if pass_rate < 70:
            report += f"""
⚠️ {category.upper()}: Low pass rate ({pass_rate:.1f}%). Needs attention.
"""

    report += f"""
{"=" * 80}
FILES GENERATED
{"=" * 80}

- Security Test Results: {RESULTS_DIR}/security_test_results.json
- RAG Evaluation Results: {RESULTS_DIR}/rag_evaluation_results.json
- Test Report: {RESULTS_DIR}/test_report.txt

{"=" * 80}
"""

    # Save report
    report_file = RESULTS_DIR / "test_report.txt"
    with open(report_file, "w") as f:
        f.write(report)

    print(report)
    print(f"\n✅ Report saved to: {report_file}")


def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(
        description="Run Giskard tests for Medical RAG Chatbot"
    )
    parser.add_argument(
        "--test-type",
        choices=["security", "rag", "all"],
        default="all",
        help="Type of tests to run",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("MEDICAL RAG CHATBOT - GISKARD TEST SUITE")
    print("=" * 80)
    print(f"\nTest Type: {args.test_type}")
    print(f"Results Directory: {RESULTS_DIR}")
    print("\n" + "=" * 80)

    security_summary = None
    rag_summary = None

    if args.test_type in ["security", "all"]:
        security_summary = run_security_tests()

    if args.test_type in ["rag", "all"]:
        rag_summary = run_rag_evaluation()

    # Generate comprehensive report
    if args.test_type == "all":
        generate_report(security_summary, rag_summary)

    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETE!")
    print("=" * 80)


if __name__ == "__main__":
    main()
