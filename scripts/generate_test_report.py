#!/usr/bin/env python3
"""
Generate Comprehensive Test Report.

Creates detailed test execution reports with trends and analysis.
"""
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def run_command(cmd):
    """Run a command and return output."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, check=False
        )
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1


def parse_pytest_output(output):
    """Parse pytest output to extract test results."""
    results = {
        'passed': 0,
        'failed': 0,
        'skipped': 0,
        'errors': 0,
        'total': 0
    }
    
    for line in output.split('\n'):
        if 'passed' in line.lower() and 'failed' in line.lower():
            # Parse line like "100 passed, 5 failed in 10.5s"
            parts = line.split()
            for i, part in enumerate(parts):
                if part.isdigit():
                    if i + 1 < len(parts):
                        if 'passed' in parts[i+1].lower():
                            results['passed'] = int(part)
                        elif 'failed' in parts[i+1].lower():
                            results['failed'] = int(part)
                        elif 'skipped' in parts[i+1].lower():
                            results['skipped'] = int(part)
                        elif 'error' in parts[i+1].lower():
                            results['errors'] = int(part)
    
    results['total'] = results['passed'] + results['failed'] + results['skipped'] + results['errors']
    return results


def get_test_coverage():
    """Get test coverage from pytest-cov."""
    stdout, stderr, code = run_command("pytest --cov=scraper --cov=app --cov-report=term-missing -q")
    
    coverage = None
    for line in stdout.split('\n'):
        if 'TOTAL' in line and '%' in line:
            try:
                parts = line.split()
                for part in parts:
                    if '%' in part:
                        coverage = float(part.replace('%', ''))
                        break
            except:
                pass
    
    return coverage


def generate_report():
    """Generate comprehensive test report."""
    report = {
        'timestamp': datetime.now().isoformat(),
        'test_results': {},
        'coverage': {},
        'summary': {}
    }
    
    # Run tests and get results
    stdout, stderr, code = run_command("pytest --tb=no -q")
    test_results = parse_pytest_output(stdout)
    report['test_results'] = test_results
    
    # Get coverage
    coverage = get_test_coverage()
    report['coverage'] = {
        'percentage': coverage,
        'target': 90.0,
        'status': 'pass' if coverage and coverage >= 90 else 'fail'
    }
    
    # Calculate summary
    total = test_results['total']
    if total > 0:
        pass_rate = (test_results['passed'] / total) * 100
        report['summary'] = {
            'total_tests': total,
            'pass_rate': pass_rate,
            'status': 'pass' if pass_rate >= 95 else 'fail'
        }
    else:
        report['summary'] = {
            'total_tests': 0,
            'pass_rate': 0,
            'status': 'fail'
        }
    
    return report


def main():
    """Main function."""
    report = generate_report()
    
    # Print report
    print("=" * 60)
    print("Test Execution Report")
    print("=" * 60)
    print(f"Timestamp: {report['timestamp']}")
    print()
    
    print("Test Results:")
    results = report['test_results']
    print(f"  Total: {results['total']}")
    print(f"  Passed: {results['passed']}")
    print(f"  Failed: {results['failed']}")
    print(f"  Skipped: {results['skipped']}")
    print(f"  Errors: {results['errors']}")
    if results['total'] > 0:
        pass_rate = (results['passed'] / results['total']) * 100
        print(f"  Pass Rate: {pass_rate:.1f}%")
    print()
    
    print("Coverage:")
    coverage = report['coverage']
    print(f"  Coverage: {coverage['percentage']}% (Target: {coverage['target']}%)")
    print(f"  Status: {coverage['status']}")
    print()
    
    print("Summary:")
    summary = report['summary']
    print(f"  Overall Status: {summary['status'].upper()}")
    print("=" * 60)
    
    # Save to file
    report_file = Path("test_report.json")
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\nReport saved to: {report_file}")
    
    return 0 if summary['status'] == 'pass' else 1


if __name__ == "__main__":
    sys.exit(main())

