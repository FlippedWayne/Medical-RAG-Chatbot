"""
PII Detector
Detects Personally Identifiable Information in text content
"""

import re
import logging
from typing import List, Dict, Optional
from .config import ValidationIssue, ValidationSeverity, PII_PATTERNS

logger = logging.getLogger(__name__)


class PIIDetector:
    """Detects Personally Identifiable Information in text"""

    def __init__(self, custom_patterns: Optional[Dict] = None):
        """
        Initialize PII Detector

        Args:
            custom_patterns: Optional custom PII patterns to add
        """
        self.patterns = PII_PATTERNS.copy()

        # Add custom patterns if provided
        if custom_patterns:
            self.patterns.update(custom_patterns)
            logger.info(f"Added {len(custom_patterns)} custom PII patterns")

        logger.info(f"PIIDetector initialized with {len(self.patterns)} patterns")

    def detect(self, text: str) -> List[ValidationIssue]:
        """
        Detect PII in the given text

        Args:
            text: Text to scan for PII

        Returns:
            List of ValidationIssue objects for each PII found
        """
        issues = []

        for pii_type, config in self.patterns.items():
            pattern = config["pattern"]
            matches = re.finditer(pattern, text, re.IGNORECASE)

            for match in matches:
                issue = ValidationIssue(
                    issue_type=f"PII_{pii_type.upper()}",
                    severity=config["severity"],
                    description=config["description"],
                    matched_text=self._mask_sensitive_data(match.group()),
                    position=match.start(),
                )
                issues.append(issue)
                logger.warning(f"PII detected: {issue}")

        return issues

    def detect_by_type(self, text: str, pii_type: str) -> List[ValidationIssue]:
        """
        Detect specific type of PII

        Args:
            text: Text to scan
            pii_type: Type of PII to detect (e.g., 'email', 'ssn')

        Returns:
            List of ValidationIssue objects for the specified PII type
        """
        if pii_type not in self.patterns:
            logger.warning(f"Unknown PII type: {pii_type}")
            return []

        issues = []
        config = self.patterns[pii_type]
        pattern = config["pattern"]
        matches = re.finditer(pattern, text, re.IGNORECASE)

        for match in matches:
            issue = ValidationIssue(
                issue_type=f"PII_{pii_type.upper()}",
                severity=config["severity"],
                description=config["description"],
                matched_text=self._mask_sensitive_data(match.group()),
                position=match.start(),
            )
            issues.append(issue)

        return issues

    def has_pii(self, text: str) -> bool:
        """
        Quick check if text contains any PII

        Args:
            text: Text to check

        Returns:
            True if PII found, False otherwise
        """
        return len(self.detect(text)) > 0

    def get_pii_count(self, text: str) -> Dict[str, int]:
        """
        Get count of each PII type found

        Args:
            text: Text to analyze

        Returns:
            Dictionary with PII type counts
        """
        issues = self.detect(text)
        counts = {}

        for issue in issues:
            pii_type = issue.issue_type
            counts[pii_type] = counts.get(pii_type, 0) + 1

        return counts

    def redact_pii(self, text: str, redaction_text: str = "[REDACTED]") -> str:
        """
        Redact all PII from text

        Args:
            text: Text to redact
            redaction_text: Text to replace PII with

        Returns:
            Text with PII redacted
        """
        redacted_text = text

        # Sort patterns by position (reverse) to avoid offset issues
        all_matches = []
        for pii_type, config in self.patterns.items():
            pattern = config["pattern"]
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                all_matches.append((match.start(), match.end(), pii_type))

        # Sort by position (reverse order)
        all_matches.sort(key=lambda x: x[0], reverse=True)

        # Replace matches
        for start, end, pii_type in all_matches:
            redacted_text = redacted_text[:start] + redaction_text + redacted_text[end:]
            logger.debug(f"Redacted {pii_type} at position {start}")

        return redacted_text

    @staticmethod
    def _mask_sensitive_data(text: str) -> str:
        """
        Mask sensitive data for logging purposes

        Args:
            text: Sensitive text to mask

        Returns:
            Masked text
        """
        if len(text) <= 4:
            return "***"
        return f"{text[:2]}***{text[-2:]}"

    def add_custom_pattern(
        self, name: str, pattern: str, severity: ValidationSeverity, description: str
    ):
        """
        Add a custom PII pattern

        Args:
            name: Name of the PII type
            pattern: Regex pattern
            severity: Severity level
            description: Description of the PII type
        """
        self.patterns[name] = {
            "pattern": pattern,
            "severity": severity,
            "description": description,
        }
        logger.info(f"Added custom PII pattern: {name}")


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    detector = PIIDetector()

    test_text = """
    Contact John Doe at john.doe@email.com or call 555-123-4567.
    SSN: 123-45-6789
    Medical Record: MRN A123456
    """

    print("Testing PII Detection:")
    print("=" * 60)

    issues = detector.detect(test_text)
    print(f"\nFound {len(issues)} PII instances:")
    for issue in issues:
        print(f"  - {issue}")

    print("\nPII Counts:")
    counts = detector.get_pii_count(test_text)
    for pii_type, count in counts.items():
        print(f"  - {pii_type}: {count}")

    print("\nRedacted Text:")
    print(detector.redact_pii(test_text))
