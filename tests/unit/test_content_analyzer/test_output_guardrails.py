"""
Unit tests for src/content_analyzer/output_guardrails.py
"""
import pytest
from unittest.mock import patch, MagicMock

from src.content_analyzer.output_guardrails import OutputGuardrails
from src.content_analyzer.config import ValidationIssue, ValidationSeverity


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pii_issue():
    return ValidationIssue(
        issue_type="PII_SSN",
        severity=ValidationSeverity.CRITICAL,
        description="SSN detected",
        matched_text="12***89",
        position=10,
    )


def _make_toxic_issue():
    return ValidationIssue(
        issue_type="TOXIC_PROFANITY",
        severity=ValidationSeverity.MEDIUM,
        description="Profanity detected",
        matched_text="d***",
        position=5,
    )


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

class TestOutputGuardrailsInit:

    def test_init_basic(self):
        """Creates pii_detector and toxic_detector; NER/Presidio disabled"""
        g = OutputGuardrails(enable_ner_check=False, enable_presidio_check=False)
        assert g.pii_detector is not None
        assert g.toxic_detector is not None
        assert g.ner_detector is None
        assert g.presidio_detector is None

    def test_init_pii_check_disabled(self):
        """enable_pii_check flag stored correctly"""
        g = OutputGuardrails(enable_pii_check=False, enable_ner_check=False,
                             enable_presidio_check=False)
        assert g.enable_pii_check is False


# ---------------------------------------------------------------------------
# validate_output
# ---------------------------------------------------------------------------

class TestValidateOutput:

    def _guardrails(self, **kwargs):
        defaults = dict(enable_ner_check=False, enable_presidio_check=False)
        defaults.update(kwargs)
        return OutputGuardrails(**defaults)

    def test_validate_output_clean(self, clean_text):
        """Clean text passes all checks"""
        # Medical keywords trigger disclaimer, so use a truly non-medical text
        non_medical = "The sky is blue and the grass is green."
        g = self._guardrails()
        is_safe, issues, safe_out = g.validate_output(non_medical)
        assert is_safe is True
        assert non_medical in safe_out

    def test_validate_output_pii_blocked(self):
        """Output with SSN is blocked"""
        g = self._guardrails(block_on_pii=True)
        text = "Patient SSN: 123-45-6789 should follow up."
        is_safe, issues, _ = g.validate_output(text)
        assert is_safe is False
        assert any(i.issue_type == "PII_SSN" for i in issues)

    def test_validate_output_toxic_blocked(self):
        """Output with profanity is blocked"""
        g = self._guardrails(block_on_toxic=True)
        text = "This damn treatment is the shit."
        is_safe, issues, _ = g.validate_output(text)
        assert is_safe is False

    def test_validate_output_adds_disclaimer(self):
        """Disclaimer appended to medical output missing one"""
        g = self._guardrails(require_medical_disclaimer=True)
        text = "The recommended treatment for this condition is rest and medication."
        _, _, safe_out = g.validate_output(text, original_query="treatment?")
        assert "Medical Disclaimer" in safe_out or "medical advice" in safe_out.lower()

    def test_validate_output_disclaimer_not_added_twice(self):
        """Disclaimer not added when output already contains one"""
        g = self._guardrails(require_medical_disclaimer=True)
        text = (
            "The treatment involves medication. "
            "Please consult with a healthcare professional for medical advice."
        )
        _, issues, safe_out = g.validate_output(text)
        # No MISSING_DISCLAIMER issues
        assert not any(i.issue_type == "MISSING_DISCLAIMER" for i in issues)

    def test_check_hallucinations_overconfident(self):
        """Detects overconfident language"""
        g = self._guardrails(enable_hallucination_check=True)
        text = "This will definitely cure your diabetes in 30 days guaranteed!"
        is_safe, issues, _ = g.validate_output(
            text, retrieved_context=["info about diabetes"]
        )
        assert any(i.issue_type == "HALLUCINATION_RISK" for i in issues)


# ---------------------------------------------------------------------------
# Fallback & sanitize
# ---------------------------------------------------------------------------

class TestFallbackAndSanitize:

    def _guardrails(self):
        return OutputGuardrails(enable_ner_check=False, enable_presidio_check=False)

    def test_get_fallback_response_pii(self):
        """Returns PII-specific fallback message"""
        g = self._guardrails()
        msg = g.get_fallback_response("pii")
        assert "sensitive information" in msg.lower()

    def test_get_fallback_response_toxic(self):
        """Returns toxic-specific fallback message"""
        g = self._guardrails()
        msg = g.get_fallback_response("toxic")
        assert "rephrase" in msg.lower()

    def test_get_fallback_response_default(self):
        """Returns safety fallback for unknown reason"""
        g = self._guardrails()
        msg = g.get_fallback_response("unknown_reason")
        assert "safety" in msg.lower() or "cannot provide" in msg.lower()

    def test_sanitize_output(self):
        """sanitize_output redacts PII and filters toxic content"""
        g = self._guardrails()
        text = "Email: tester@example.com. You idiot."
        sanitized = g.sanitize_output(text)
        assert "tester@example.com" not in sanitized
        assert "idiot" not in sanitized.lower()


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

class TestDeduplication:

    def test_deduplicate_pii_issues_removes_dupes(self):
        """Removes duplicate issues with same position and matched_text"""
        g = OutputGuardrails(enable_ner_check=False, enable_presidio_check=False)
        issue_a = _make_pii_issue()
        issue_b = _make_pii_issue()  # exact same position & matched_text
        unique = g._deduplicate_pii_issues([issue_a, issue_b])
        assert len(unique) == 1

    def test_deduplicate_pii_issues_keeps_different(self):
        """Keeps issues with different positions"""
        g = OutputGuardrails(enable_ner_check=False, enable_presidio_check=False)
        issue_a = ValidationIssue("PII_SSN", ValidationSeverity.CRITICAL, "desc",
                                   "12***89", 10)
        issue_b = ValidationIssue("PII_SSN", ValidationSeverity.CRITICAL, "desc",
                                   "12***89", 50)
        unique = g._deduplicate_pii_issues([issue_a, issue_b])
        assert len(unique) == 2

    def test_deduplicate_empty_list(self):
        """Returns empty list when input is empty"""
        g = OutputGuardrails(enable_ner_check=False, enable_presidio_check=False)
        assert g._deduplicate_pii_issues([]) == []
