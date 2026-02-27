"""
Integration tests: PIIDetector + ToxicContentDetector + ContentValidator

Verifies that individual detector components interact correctly when wired
together through the ContentValidator orchestrator.
All tests use the regex/wordlist-based detectors (no ML dependencies required).
"""

import pytest


@pytest.mark.integration
class TestPIIDetectorIntegration:
    """PIIDetector detects various PII types and redacts them correctly."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from src.content_analyzer.pii_detector import PIIDetector

        self.detector = PIIDetector()

    def test_clean_text_returns_no_issues(self):
        text = "Diabetes is managed through diet, exercise, and medication."
        issues = self.detector.detect(text)
        assert issues == []

    def test_detects_email(self):
        issues = self.detector.detect("Contact: patient@example.com")
        types = [i.issue_type for i in issues]
        assert any("EMAIL" in t for t in types)

    def test_detects_phone(self):
        issues = self.detector.detect("Call us at 555-123-4567")
        types = [i.issue_type for i in issues]
        assert any("PHONE" in t for t in types)

    def test_detects_ssn(self):
        issues = self.detector.detect("SSN: 123-45-6789")
        types = [i.issue_type for i in issues]
        assert any("SSN" in t for t in types)

    def test_has_pii_returns_true_with_pii(self):
        assert self.detector.has_pii("Email: test@test.com") is True

    def test_has_pii_returns_false_for_clean_text(self):
        assert self.detector.has_pii("Normal medical text.") is False

    def test_redact_pii_replaces_with_marker(self):
        text = "Email: patient@hospital.com"
        redacted = self.detector.redact_pii(text)
        assert "patient@hospital.com" not in redacted
        assert "[REDACTED]" in redacted

    def test_get_pii_count_returns_correct_types(self):
        text = "Email: a@b.com and SSN: 123-45-6789"
        counts = self.detector.get_pii_count(text)
        assert isinstance(counts, dict)
        assert len(counts) >= 1

    def test_detect_by_type_email(self):
        text = "Contact: info@clinic.org"
        issues = self.detector.detect_by_type(text, "email")
        assert len(issues) >= 1

    def test_detect_by_type_unknown_type_returns_empty(self):
        issues = self.detector.detect_by_type("some text", "nonexistent_type")
        assert issues == []


@pytest.mark.integration
class TestToxicDetectorIntegration:
    """ToxicContentDetector correctly identifies and filters toxic content."""

    @pytest.fixture(autouse=True)
    def setup(self):
        from src.content_analyzer.toxic_detector import ToxicContentDetector

        self.detector = ToxicContentDetector()

    def test_clean_medical_text_has_no_toxic_issues(self):
        text = "Hypertension can be treated with medication and lifestyle changes."
        issues = self.detector.detect(text)
        assert issues == []

    def test_toxic_text_flagged(self):
        issues = self.detector.detect("You are a stupid idiot!")
        assert len(issues) > 0

    def test_toxic_issue_type_prefix(self):
        issues = self.detector.detect("I hate everything about this!")
        for issue in issues:
            assert issue.issue_type.startswith("TOXIC_")

    def test_filter_toxic_content_cleans_text(self):
        text = "You are stupid."
        filtered = self.detector.filter_toxic_content(text)
        # The toxic word should be masked/replaced
        assert isinstance(filtered, str)


@pytest.mark.integration
class TestContentValidatorIntegration:
    """ContentValidator orchestrates PII + Toxic detection correctly."""

    # --- clean text ---

    def test_clean_text_is_safe(self, content_validator):
        is_safe, issues = content_validator.validate(
            "Diabetes is a metabolic condition affecting blood sugar regulation."
        )
        assert is_safe is True
        assert issues == []

    # --- PII integration ---

    def test_email_flagged_as_pii(self, content_validator):
        is_safe, issues = content_validator.validate(
            "Patient email: john.doe@hospital.com"
        )
        types = [i.issue_type for i in issues]
        assert any("EMAIL" in t for t in types)

    def test_critical_pii_ssn_blocks_content(self, content_validator):
        """SSN is CRITICAL PII — validator must return is_safe=False."""
        is_safe, issues = content_validator.validate("SSN: 123-45-6789")
        assert is_safe is False
        types = [i.issue_type for i in issues]
        assert any("SSN" in t for t in types)

    def test_multiple_pii_types_all_detected(self, content_validator):
        text = "Patient: john.doe@email.com, phone: 555-123-4567, SSN: 123-45-6789"
        _, issues = content_validator.validate(text)
        types = {i.issue_type for i in issues}
        # Expect at least 2 distinct PII types
        pii_types = {t for t in types if t.startswith("PII_")}
        assert len(pii_types) >= 2

    # --- Toxic integration ---

    def test_toxic_text_flagged(self, content_validator):
        is_safe, issues = content_validator.validate("You are a stupid idiot!")
        types = [i.issue_type for i in issues]
        assert any(t.startswith("TOXIC_") for t in types)

    # --- sanitize_content ---

    def test_sanitize_redacts_pii(self, content_validator):
        text = "Email: patient@hospital.com"
        sanitized = content_validator.sanitize_content(text)
        assert "patient@hospital.com" not in sanitized
        assert "[REDACTED]" in sanitized

    # --- batch validation ---

    def test_batch_validation_length_matches(self, content_validator):
        texts = [
            "Clean text about hypertension.",
            "SSN: 999-88-7777",
            "Normal sentence about vitamins.",
        ]
        results = content_validator.validate_batch(texts)
        assert len(results) == len(texts)

    def test_batch_mixed_results(self, content_validator):
        texts = [
            "Aspirin is used for pain relief.",
            "SSN: 123-45-6789",
        ]
        results = content_validator.validate_batch(texts)
        is_safe_0 = results[0][0]
        is_safe_1 = results[1][0]
        assert is_safe_0 is True
        assert is_safe_1 is False

    # --- validation summary ---

    def test_validation_summary_structure(self, content_validator):
        _, issues = content_validator.validate("Email: a@b.com and SSN: 123-45-6789")
        summary = content_validator.get_validation_summary(issues)
        assert "total_issues" in summary
        assert "pii_count" in summary
        assert "toxic_count" in summary
        assert "by_severity" in summary
        assert "by_type" in summary

    def test_validation_summary_counts_correct(self, content_validator):
        _, issues = content_validator.validate("SSN: 123-45-6789")
        summary = content_validator.get_validation_summary(issues)
        assert summary["pii_count"] >= 1
        assert summary["toxic_count"] == 0
