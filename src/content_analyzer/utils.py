"""
Utility functions for Content Analyzer
Helper functions for content analysis and validation
"""

import re
from typing import List, Dict, Any
from .config import ValidationIssue, ValidationSeverity


def format_validation_report(
    issues: List[ValidationIssue], include_details: bool = True
) -> str:
    """
    Format validation issues into a readable report

    Args:
        issues: List of validation issues
        include_details: Whether to include detailed information

    Returns:
        Formatted report string
    """
    if not issues:
        return "✅ No validation issues found"

    report = []
    report.append(f"❌ Found {len(issues)} validation issue(s):\n")

    # Group by severity
    by_severity = {}
    for issue in issues:
        severity = issue.severity.value
        if severity not in by_severity:
            by_severity[severity] = []
        by_severity[severity].append(issue)

    # Display by severity (critical first)
    severity_order = ["critical", "high", "medium", "low"]
    for severity in severity_order:
        if severity in by_severity:
            report.append(f"\n{severity.upper()} ({len(by_severity[severity])}):")
            for issue in by_severity[severity]:
                if include_details:
                    report.append(f"  - {issue}")
                else:
                    report.append(f"  - {issue.issue_type}: {issue.description}")

    return "\n".join(report)


def calculate_risk_score(issues: List[ValidationIssue]) -> float:
    """
    Calculate overall risk score based on validation issues

    Args:
        issues: List of validation issues

    Returns:
        Risk score from 0.0 (safe) to 10.0 (critical risk)
    """
    if not issues:
        return 0.0

    severity_weights = {
        ValidationSeverity.LOW: 1.0,
        ValidationSeverity.MEDIUM: 3.0,
        ValidationSeverity.HIGH: 6.0,
        ValidationSeverity.CRITICAL: 10.0,
    }

    total_score = sum(severity_weights.get(issue.severity, 1.0) for issue in issues)

    # Average score, capped at 10.0
    return min(10.0, total_score / len(issues))


def get_severity_color(severity: ValidationSeverity) -> str:
    """
    Get color code for severity level (for terminal output)

    Args:
        severity: Validation severity

    Returns:
        ANSI color code
    """
    colors = {
        ValidationSeverity.LOW: "\033[92m",  # Green
        ValidationSeverity.MEDIUM: "\033[93m",  # Yellow
        ValidationSeverity.HIGH: "\033[91m",  # Red
        ValidationSeverity.CRITICAL: "\033[95m",  # Magenta
    }
    return colors.get(severity, "\033[0m")


def filter_issues_by_severity(
    issues: List[ValidationIssue], min_severity: ValidationSeverity
) -> List[ValidationIssue]:
    """
    Filter issues by minimum severity level

    Args:
        issues: List of validation issues
        min_severity: Minimum severity to include

    Returns:
        Filtered list of issues
    """
    severity_order = {
        ValidationSeverity.LOW: 0,
        ValidationSeverity.MEDIUM: 1,
        ValidationSeverity.HIGH: 2,
        ValidationSeverity.CRITICAL: 3,
    }

    min_level = severity_order.get(min_severity, 0)

    return [
        issue for issue in issues if severity_order.get(issue.severity, 0) >= min_level
    ]


def group_issues_by_type(
    issues: List[ValidationIssue],
) -> Dict[str, List[ValidationIssue]]:
    """
    Group validation issues by type

    Args:
        issues: List of validation issues

    Returns:
        Dictionary mapping issue type to list of issues
    """
    grouped = {}
    for issue in issues:
        if issue.issue_type not in grouped:
            grouped[issue.issue_type] = []
        grouped[issue.issue_type].append(issue)

    return grouped


def create_validation_metrics(issues: List[ValidationIssue]) -> Dict[str, Any]:
    """
    Create comprehensive validation metrics

    Args:
        issues: List of validation issues

    Returns:
        Dictionary with validation metrics
    """
    metrics = {
        "total_issues": len(issues),
        "risk_score": calculate_risk_score(issues),
        "severity_breakdown": {"critical": 0, "high": 0, "medium": 0, "low": 0},
        "type_breakdown": {},
        "has_pii": False,
        "has_toxic_content": False,
        "is_safe": len(issues) == 0,
    }

    for issue in issues:
        # Count by severity
        metrics["severity_breakdown"][issue.severity.value] += 1

        # Count by type
        if issue.issue_type not in metrics["type_breakdown"]:
            metrics["type_breakdown"][issue.issue_type] = 0
        metrics["type_breakdown"][issue.issue_type] += 1

        # Check for PII and toxic content
        if issue.issue_type.startswith("PII_"):
            metrics["has_pii"] = True
        if issue.issue_type.startswith("TOXIC_"):
            metrics["has_toxic_content"] = True

    return metrics


def sanitize_for_logging(text: str, max_length: int = 100) -> str:
    """
    Sanitize text for safe logging (truncate and remove sensitive patterns)

    Args:
        text: Text to sanitize
        max_length: Maximum length of output

    Returns:
        Sanitized text
    """
    # Truncate
    if len(text) > max_length:
        text = text[:max_length] + "..."

    # Remove potential sensitive patterns (basic)
    text = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN]", text)  # SSN
    text = re.sub(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL]", text
    )  # Email
    text = re.sub(
        r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "[CARD]", text
    )  # Credit card

    return text


def export_issues_to_dict(issues: List[ValidationIssue]) -> List[Dict[str, Any]]:
    """
    Export validation issues to dictionary format (for JSON serialization)

    Args:
        issues: List of validation issues

    Returns:
        List of dictionaries representing issues
    """
    return [
        {
            "issue_type": issue.issue_type,
            "severity": issue.severity.value,
            "description": issue.description,
            "matched_text": issue.matched_text,
            "position": issue.position,
        }
        for issue in issues
    ]


# Example usage
if __name__ == "__main__":
    from .config import ValidationIssue, ValidationSeverity

    # Create sample issues
    sample_issues = [
        ValidationIssue(
            issue_type="PII_EMAIL",
            severity=ValidationSeverity.HIGH,
            description="Email address detected",
            matched_text="jo***om",
        ),
        ValidationIssue(
            issue_type="PII_SSN",
            severity=ValidationSeverity.CRITICAL,
            description="SSN detected",
            matched_text="12***89",
        ),
        ValidationIssue(
            issue_type="TOXIC_PROFANITY",
            severity=ValidationSeverity.MEDIUM,
            description="Profanity detected",
            matched_text="d***",
        ),
    ]

    print("Validation Report:")
    print("=" * 60)
    print(format_validation_report(sample_issues))

    print("\n\nValidation Metrics:")
    print("=" * 60)
    metrics = create_validation_metrics(sample_issues)
    for key, value in metrics.items():
        print(f"{key}: {value}")

    print(f"\n\nRisk Score: {calculate_risk_score(sample_issues):.1f}/10.0")
