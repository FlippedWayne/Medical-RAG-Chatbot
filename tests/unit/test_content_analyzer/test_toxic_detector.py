"""
Unit tests for src/content_analyzer/toxic_detector.py
"""

from src.content_analyzer.toxic_detector import ToxicContentDetector
from src.content_analyzer.config import ValidationSeverity


class TestToxicContentDetectorInit:
    def test_init_default_categories(self):
        """Loads all default TOXIC_CATEGORIES on init"""
        detector = ToxicContentDetector()
        assert len(detector.categories) > 0
        assert "profanity" in detector.categories
        assert "harassment" in detector.categories
        assert "hate_speech" in detector.categories

    def test_init_custom_categories(self):
        """Merges custom categories with defaults"""
        custom = {
            "medical_misinformation": {
                "words": ["miracle cure", "guaranteed fix"],
                "severity": ValidationSeverity.HIGH,
                "description": "Medical misinformation detected",
            }
        }
        detector = ToxicContentDetector(custom_words=custom)
        assert "medical_misinformation" in detector.categories


class TestToxicContentDetectorDetect:
    def test_detect_profanity(self):
        """Detects profanity word"""
        detector = ToxicContentDetector()
        issues = detector.detect("This damn thing doesn't work!")
        assert any(i.issue_type == "TOXIC_PROFANITY" for i in issues)

    def test_detect_harassment(self):
        """Detects harassment keywords"""
        detector = ToxicContentDetector()
        issues = detector.detect("You are a stupid idiot!")
        types = [i.issue_type for i in issues]
        assert "TOXIC_HARASSMENT" in types

    def test_detect_clean_text(self, clean_text):
        """Returns empty list for clean medical text"""
        detector = ToxicContentDetector()
        issues = detector.detect(clean_text)
        assert issues == []

    def test_detect_by_category_known(self):
        """Returns issues for specified category only"""
        detector = ToxicContentDetector()
        issues = detector.detect_by_category("You stupid moron!", "harassment")
        assert all(i.issue_type == "TOXIC_HARASSMENT" for i in issues)
        assert len(issues) > 0

    def test_detect_by_category_unknown(self):
        """Returns empty list for unknown category"""
        detector = ToxicContentDetector()
        issues = detector.detect_by_category("some text", "unknown_category")
        assert issues == []


class TestToxicContentDetectorHelpers:
    def test_has_toxic_content_true(self, toxic_text):
        """has_toxic_content returns True for toxic text"""
        detector = ToxicContentDetector()
        assert detector.has_toxic_content(toxic_text) is True

    def test_has_toxic_content_false(self, clean_text):
        """has_toxic_content returns False for clean text"""
        detector = ToxicContentDetector()
        assert detector.has_toxic_content(clean_text) is False

    def test_get_toxicity_score_zero(self, clean_text):
        """Score is 0.0 for clean text"""
        detector = ToxicContentDetector()
        score = detector.get_toxicity_score(clean_text)
        assert score == 0.0

    def test_get_toxicity_score_nonzero(self, toxic_text):
        """Score is > 0 for toxic text"""
        detector = ToxicContentDetector()
        score = detector.get_toxicity_score(toxic_text)
        assert score > 0.0
        assert score <= 1.0

    def test_get_category_counts(self, toxic_text):
        """Returns dict of category counts"""
        detector = ToxicContentDetector()
        counts = detector.get_category_counts(toxic_text)
        assert isinstance(counts, dict)
        assert sum(counts.values()) > 0

    def test_filter_toxic_content(self):
        """filter_toxic_content replaces toxic words with [FILTERED]"""
        detector = ToxicContentDetector()
        result = detector.filter_toxic_content("You idiot!", "[FILTERED]")
        assert "idiot" not in result.lower()
        assert "[FILTERED]" in result

    def test_add_custom_category(self):
        """add_custom_category adds category to self.categories"""
        detector = ToxicContentDetector()
        detector.add_custom_category(
            name="spam",
            words=["click here", "free money"],
            severity=ValidationSeverity.LOW,
            description="Spam content detected",
        )
        assert "spam" in detector.categories
        assert "click here" in detector.categories["spam"]["words"]

    def test_mask_toxic_word_short(self):
        """Short words (<=2 chars) return ***"""
        result = ToxicContentDetector._mask_toxic_word("it")
        assert result == "***"

    def test_mask_toxic_word_long(self):
        """Longer words have first char + ***"""
        result = ToxicContentDetector._mask_toxic_word("hate")
        assert result.startswith("h")
        assert "***" in result
