"""
Test runner script for FastAPI Versioner test suite.

This script runs the comprehensive test suite and generates reports.
"""

import subprocess
import sys
import time
from pathlib import Path


def run_command(command: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'=' * 60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(command)}")
    print(f"{'=' * 60}")

    start_time = time.time()

    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)

        end_time = time.time()
        duration = end_time - start_time

        print(f"Duration: {duration:.2f}s")
        print(f"Exit code: {result.returncode}")

        if result.stdout:
            print(f"\nSTDOUT:\n{result.stdout}")

        if result.stderr:
            print(f"\nSTDERR:\n{result.stderr}")

        return result.returncode == 0

    except Exception as e:
        print(f"Error running command: {e}")
        return False


def main():
    """Run the complete test suite."""
    print("FastAPI Versioner - Comprehensive Test Suite")
    print("=" * 60)

    # Change to project root
    project_root = Path(__file__).parent.parent
    print(f"Project root: {project_root}")

    # Test commands to run
    test_commands = [
        {
            "command": ["python", "-m", "pytest", "tests/unit/", "-v", "--tb=short"],
            "description": "Unit Tests",
            "required": True,
        },
        {
            "command": [
                "python",
                "-m",
                "pytest",
                "tests/integration/",
                "-v",
                "--tb=short",
            ],
            "description": "Integration Tests",
            "required": True,
        },
        {
            "command": [
                "python",
                "-m",
                "pytest",
                "tests/performance/",
                "-v",
                "--tb=short",
                "-s",
            ],
            "description": "Performance Tests",
            "required": False,
        },
        {
            "command": [
                "python",
                "-m",
                "pytest",
                "tests/",
                "--cov=src/fastapi_versioner",
                "--cov-report=term-missing",
                "--cov-report=html",
            ],
            "description": "Coverage Report",
            "required": False,
        },
        {
            "command": [
                "python",
                "-m",
                "pytest",
                "tests/",
                "--cov=src/fastapi_versioner",
                "--cov-fail-under=80",
            ],
            "description": "Coverage Threshold Check (80%)",
            "required": False,
        },
    ]

    # Run tests
    results = []

    for test_config in test_commands:
        success = run_command(test_config["command"], test_config["description"])
        results.append(
            {
                "description": test_config["description"],
                "success": success,
                "required": test_config["required"],
            }
        )

        if not success and test_config["required"]:
            print(f"\n❌ CRITICAL FAILURE: {test_config['description']} failed!")
            print("Stopping test execution due to critical failure.")
            break

    # Print summary
    print(f"\n{'=' * 60}")
    print("TEST SUITE SUMMARY")
    print(f"{'=' * 60}")

    total_tests = len(results)
    passed_tests = sum(1 for r in results if r["success"])
    failed_tests = total_tests - passed_tests

    for result in results:
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        required = " (REQUIRED)" if result["required"] else " (OPTIONAL)"
        print(f"{status} {result['description']}{required}")

    print(f"\nTotal: {total_tests}, Passed: {passed_tests}, Failed: {failed_tests}")

    # Determine overall result
    critical_failures = sum(1 for r in results if not r["success"] and r["required"])

    if critical_failures == 0:
        print("\n🎉 TEST SUITE PASSED! All critical tests successful.")
        if failed_tests > 0:
            print(f"Note: {failed_tests} optional tests failed.")
        return 0
    else:
        print(f"\n💥 TEST SUITE FAILED! {critical_failures} critical test(s) failed.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
