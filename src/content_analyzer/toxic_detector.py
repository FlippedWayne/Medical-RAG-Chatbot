"""
Toxic Content Detector
Detects toxic, offensive, or inappropriate content in text
"""

import re
import logging
from typing import List, Dict, Optional
from .config import ValidationIssue, ValidationSeverity, TOXIC_CATEGORIES

logger = logging.getLogger(__name__)


class ToxicContentDetector:
    """Detects toxic, offensive, or inappropriate content"""

    def __init__(self, custom_words: Optional[Dict] = None):
        """
        Initialize Toxic Content Detector

        Args:
            custom_words: Optional custom toxic word categories to add
        """
        self.categories = TOXIC_CATEGORIES.copy()

        # Add custom categories if provided
        if custom_words:
            self.categories.update(custom_words)
            logger.info(f"Added {len(custom_words)} custom toxic categories")

        logger.info(
            f"ToxicContentDetector initialized with {len(self.categories)} categories"
        )

    def detect(self, text: str) -> List[ValidationIssue]:
        """
        Detect toxic content in the given text

        Args:
            text: Text to scan for toxic content

        Returns:
            List of ValidationIssue objects for each toxic content found
        """
        issues = []
        text_lower = text.lower()

        for category, config in self.categories.items():
            for word in config["words"]:
                # Use word boundaries to avoid false positives
                pattern = r"\b" + re.escape(word) + r"\b"
                matches = re.finditer(pattern, text_lower)

                for match in matches:
                    issue = ValidationIssue(
                        issue_type=f"TOXIC_{category.upper()}",
                        severity=config["severity"],
                        description=config["description"],
                        matched_text=self._mask_toxic_word(word),
                        position=match.start(),
                    )
                    issues.append(issue)
                    logger.warning(f"Toxic content detected: {issue}")

        return issues

    def detect_by_category(self, text: str, category: str) -> List[ValidationIssue]:
        """
        Detect specific category of toxic content

        Args:
            text: Text to scan
            category: Category to detect (e.g., 'profanity', 'hate_speech')

        Returns:
            List of ValidationIssue objects for the specified category
        """
        if category not in self.categories:
            logger.warning(f"Unknown toxic category: {category}")
            return []

        issues = []
        text_lower = text.lower()
        config = self.categories[category]

        for word in config["words"]:
            pattern = r"\b" + re.escape(word) + r"\b"
            matches = re.finditer(pattern, text_lower)

            for match in matches:
                issue = ValidationIssue(
                    issue_type=f"TOXIC_{category.upper()}",
                    severity=config["severity"],
                    description=config["description"],
                    matched_text=self._mask_toxic_word(word),
                    position=match.start(),
                )
                issues.append(issue)

        return issues

    def has_toxic_content(self, text: str) -> bool:
        """
        Quick check if text contains toxic content

        Args:
            text: Text to check

        Returns:
            True if toxic content found, False otherwise
        """
        return len(self.detect(text)) > 0

    def get_toxicity_score(self, text: str) -> float:
        """
        Calculate a simple toxicity score (0.0 to 1.0)

        Args:
            text: Text to analyze

        Returns:
            Toxicity score (higher = more toxic)
        """
        issues = self.detect(text)

        if not issues:
            return 0.0

        # Weight by severity
        severity_weights = {
            ValidationSeverity.LOW: 0.25,
            ValidationSeverity.MEDIUM: 0.5,
            ValidationSeverity.HIGH: 0.75,
            ValidationSeverity.CRITICAL: 1.0,
        }

        total_score = sum(severity_weights.get(issue.severity, 0.5) for issue in issues)

        # Normalize by text length (words)
        word_count = len(text.split())
        if word_count == 0:
            return 0.0

        # Cap at 1.0
        return min(1.0, total_score / word_count)

    def get_category_counts(self, text: str) -> Dict[str, int]:
        """
        Get count of each toxic category found

        Args:
            text: Text to analyze

        Returns:
            Dictionary with category counts
        """
        issues = self.detect(text)
        counts = {}

        for issue in issues:
            category = issue.issue_type
            counts[category] = counts.get(category, 0) + 1

        return counts

    def filter_toxic_content(self, text: str, replacement: str = "[FILTERED]") -> str:
        """
        Filter toxic words from text

        Args:
            text: Text to filter
            replacement: Text to replace toxic words with

        Returns:
            Text with toxic words filtered
        """
        filtered_text = text
        text_lower = text.lower()

        # Collect all matches
        all_matches = []
        for category, config in self.categories.items():
            for word in config["words"]:
                pattern = r"\b" + re.escape(word) + r"\b"
                matches = re.finditer(pattern, text_lower)
                for match in matches:
                    all_matches.append((match.start(), match.end()))

        # Sort by position (reverse order)
        all_matches.sort(key=lambda x: x[0], reverse=True)

        # Replace matches
        for start, end in all_matches:
            filtered_text = filtered_text[:start] + replacement + filtered_text[end:]

        return filtered_text

    @staticmethod
    def _mask_toxic_word(word: str) -> str:
        """
        Mask toxic word for logging

        Args:
            word: Toxic word to mask

        Returns:
            Masked word
        """
        if len(word) <= 2:
            return "***"
        return f"{word[0]}***"

    def add_custom_category(
        self,
        name: str,
        words: List[str],
        severity: ValidationSeverity,
        description: str,
    ):
        """
        Add a custom toxic content category

        Args:
            name: Name of the category
            words: List of toxic words
            severity: Severity level
            description: Description of the category
        """
        self.categories[name] = {
            "words": words,
            "severity": severity,
            "description": description,
        }
        logger.info(f"Added custom toxic category: {name}")


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    detector = ToxicContentDetector()

    test_texts = [
        "This is a clean medical text about diabetes.",
        "This damn thing doesn't work!",
        "I hate this stupid system.",
        "You're an idiot and a moron!",
    ]

    print("Testing Toxic Content Detection:")
    print("=" * 60)

    for i, text in enumerate(test_texts, 1):
        print(f"\nTest {i}: {text}")
        print("-" * 60)

        issues = detector.detect(text)
        if issues:
            print(f"❌ Found {len(issues)} toxic content:")
            for issue in issues:
                print(f"  - {issue}")

            score = detector.get_toxicity_score(text)
            print(f"Toxicity Score: {score:.2f}")

            print(f"Filtered: {detector.filter_toxic_content(text)}")
        else:
            print("✅ No toxic content found")
