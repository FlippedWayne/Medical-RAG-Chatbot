"""
Unit tests for src/content_analyzer/pii_detector.py
"""

from src.content_analyzer.pii_detector import PIIDetector
from src.content_analyzer.config import ValidationSeverity


class TestPIIDetectorInit:
    def test_init_default_patterns(self):
        """Loads all default PII_PATTERNS on init"""
        detector = PIIDetector()
        assert len(detector.patterns) > 0
        assert "email" in detector.patterns
        assert "ssn" in detector.patterns

    def test_init_custom_patterns(self):
        """Merges custom patterns with defaults"""
        custom = {
            "custom_id": {
                "pattern": r"\bCUSTOM-\d{6}\b",
                "severity": ValidationSeverity.HIGH,
                "description": "Custom ID detected",
            }
        }
        detector = PIIDetector(custom_patterns=custom)
        assert "custom_id" in detector.patterns


class TestPIIDetectorDetect:
    def test_detect_email(self):
        """Detects email address"""
        detector = PIIDetector()
        issues = detector.detect("Contact me at john.doe@email.com please.")
        types = [i.issue_type for i in issues]
        assert "PII_EMAIL" in types

    def test_detect_ssn(self):
        """Detects SSN with CRITICAL severity"""
        detector = PIIDetector()
        issues = detector.detect("SSN: 123-45-6789")
        assert any(i.issue_type == "PII_SSN" for i in issues)
        assert any(i.severity == ValidationSeverity.CRITICAL for i in issues)

    def test_detect_phone(self):
        """Detects phone number"""
        detector = PIIDetector()
        issues = detector.detect("Call me at 555-123-4567.")
        assert any(i.issue_type == "PII_PHONE" for i in issues)

    def test_detect_credit_card(self):
        """Detects credit card number"""
        detector = PIIDetector()
        issues = detector.detect("Card: 1234-5678-9012-3456")
        assert any(i.issue_type == "PII_CREDIT_CARD" for i in issues)

    def test_detect_medical_record(self):
        """Detects medical record number"""
        detector = PIIDetector()
        issues = detector.detect("MRN A123456 needs follow-up.")
        assert any(i.issue_type == "PII_MEDICAL_RECORD" for i in issues)

    def test_detect_no_pii(self, clean_text):
        """Returns empty list for clean text"""
        detector = PIIDetector()
        issues = detector.detect(clean_text)
        assert issues == []

    def test_detect_by_type_known(self):
        """Returns issues for a specified PII type"""
        detector = PIIDetector()
        issues = detector.detect_by_type("john.doe@email.com", "email")
        assert len(issues) == 1
        assert issues[0].issue_type == "PII_EMAIL"

    def test_detect_by_type_unknown(self):
        """Returns empty list for unknown PII type"""
        detector = PIIDetector()
        issues = detector.detect_by_type("some text", "nonexistent_type")
        assert issues == []


class TestPIIDetectorHelpers:
    def test_has_pii_true(self, pii_text):
        """has_pii returns True when PII present"""
        detector = PIIDetector()
        assert detector.has_pii(pii_text) is True

    def test_has_pii_false(self, clean_text):
        """has_pii returns False for clean text"""
        detector = PIIDetector()
        assert detector.has_pii(clean_text) is False

    def test_get_pii_count(self, pii_text):
        """get_pii_count returns a non-empty dict"""
        detector = PIIDetector()
        counts = detector.get_pii_count(pii_text)
        assert isinstance(counts, dict)
        assert sum(counts.values()) > 0

    def test_redact_pii(self):
        """redact_pii replaces PII with [REDACTED]"""
        detector = PIIDetector()
        text = "Email: test@example.com"
        redacted = detector.redact_pii(text)
        assert "[REDACTED]" in redacted
        assert "test@example.com" not in redacted

    def test_mask_sensitive_data_short(self):
        """Short text (<=4 chars) is fully masked"""
        result = PIIDetector._mask_sensitive_data("abc")
        assert result == "***"

    def test_mask_sensitive_data_long(self):
        """Long text is partially masked"""
        result = PIIDetector._mask_sensitive_data("john.doe@email.com")
        assert result.startswith("jo")
        assert "***" in result
        assert result.endswith("om")

    def test_add_custom_pattern(self):
        """add_custom_pattern adds to self.patterns"""
        detector = PIIDetector()
        detector.add_custom_pattern(
            name="employee_id",
            pattern=r"\bEMP-\d{5}\b",
            severity=ValidationSeverity.MEDIUM,
            description="Employee ID detected",
        )
        assert "employee_id" in detector.patterns
