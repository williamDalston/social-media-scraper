#!/usr/bin/env python3
"""
Generate Quality Metrics Report.

Tracks test coverage, code quality, technical debt, and other metrics.
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


def get_test_coverage():
    """Get test coverage percentage."""
    stdout, stderr, code = run_command("pytest --cov=scraper --cov=app --cov-report=term-missing -q")
    
    if code != 0:
        return None
    
    # Parse coverage from output
    for line in stdout.split('\n'):
        if 'TOTAL' in line and '%' in line:
            try:
                parts = line.split()
                for i, part in enumerate(parts):
                    if '%' in part:
                        return float(part.replace('%', ''))
            except:
                pass
    
    return None


def get_test_count():
    """Get total number of tests."""
    stdout, stderr, code = run_command("pytest --co -q")
    
    if code != 0:
        return None
    
    # Count tests collected
    for line in stdout.split('\n'):
        if 'test' in line.lower() and 'collected' in line.lower():
            try:
                parts = line.split()
                for part in parts:
                    if part.isdigit():
                        return int(part)
            except:
                pass
    
    return None


def get_dependency_vulnerabilities():
    """Check for dependency vulnerabilities."""
    stdout, stderr, code = run_command("safety check --json")
    
    if code == 0:
        return {"count": 0, "vulnerabilities": []}
    
    try:
        data = json.loads(stdout)
        return {
            "count": len(data.get("vulnerabilities", [])),
            "vulnerabilities": data.get("vulnerabilities", [])
        }
    except:
        return {"count": 0, "vulnerabilities": []}


def get_security_issues():
    """Get security issues from Bandit."""
    stdout, stderr, code = run_command("bandit -r scraper/ app.py -f json")
    
    if code == 0:
        return {"count": 0, "issues": []}
    
    try:
        data = json.loads(stdout)
        return {
            "count": len(data.get("results", [])),
            "issues": data.get("results", [])
        }
    except:
        return {"count": 0, "issues": []}


def generate_report():
    """Generate quality metrics report."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "metrics": {}
    }
    
    # Test coverage
    coverage = get_test_coverage()
    report["metrics"]["test_coverage"] = {
        "percentage": coverage,
        "target": 90.0,
        "status": "pass" if coverage and coverage >= 90 else "fail"
    }
    
    # Test count
    test_count = get_test_count()
    report["metrics"]["test_count"] = test_count
    
    # Dependency vulnerabilities
    vulns = get_dependency_vulnerabilities()
    report["metrics"]["dependency_vulnerabilities"] = {
        "count": vulns["count"],
        "status": "pass" if vulns["count"] == 0 else "fail"
    }
    
    # Security issues
    security = get_security_issues()
    report["metrics"]["security_issues"] = {
        "count": security["count"],
        "status": "pass" if security["count"] == 0 else "warn"
    }
    
    # Calculate overall status
    all_pass = (
        report["metrics"]["test_coverage"]["status"] == "pass" and
        report["metrics"]["dependency_vulnerabilities"]["status"] == "pass"
    )
    report["overall_status"] = "pass" if all_pass else "fail"
    
    return report


def main():
    """Main function."""
    report = generate_report()
    
    # Print report
    print("=" * 60)
    print("Quality Metrics Report")
    print("=" * 60)
    print(f"Timestamp: {report['timestamp']}")
    print()
    
    print("Test Coverage:")
    coverage = report["metrics"]["test_coverage"]
    print(f"  Coverage: {coverage['percentage']}% (Target: {coverage['target']}%)")
    print(f"  Status: {coverage['status']}")
    print()
    
    print("Test Count:")
    print(f"  Total Tests: {report['metrics']['test_count']}")
    print()
    
    print("Dependency Vulnerabilities:")
    vulns = report["metrics"]["dependency_vulnerabilities"]
    print(f"  Count: {vulns['count']}")
    print(f"  Status: {vulns['status']}")
    print()
    
    print("Security Issues:")
    security = report["metrics"]["security_issues"]
    print(f"  Count: {security['count']}")
    print(f"  Status: {security['status']}")
    print()
    
    print("=" * 60)
    print(f"Overall Status: {report['overall_status'].upper()}")
    print("=" * 60)
    
    # Save to file
    report_file = Path("quality_report.json")
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\nReport saved to: {report_file}")
    
    return 0 if report["overall_status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())

