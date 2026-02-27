"""
Enhanced Toxic Content Detector using Detoxify
Provides ML-based, context-aware toxic content detection with higher accuracy
"""

import logging
from typing import List, Dict

try:
    from detoxify import Detoxify as DetoxifyModel

    DETOXIFY_AVAILABLE = True
except ImportError:
    DETOXIFY_AVAILABLE = False

from .config import ValidationIssue, ValidationSeverity

logger = logging.getLogger(__name__)


class ToxicContentDetectorML:
    """
    Enhanced toxic content detector using Detoxify ML model

    Features:
    - ML-based toxicity detection
    - Context-aware analysis
    - Multiple toxicity categories
    - Confidence scores
    - Reduced false positives
    """

    # Map Detoxify categories to severity levels
    CATEGORY_SEVERITY_MAP = {
        # CRITICAL - Must be blocked
        "severe_toxicity": ValidationSeverity.CRITICAL,
        "threat": ValidationSeverity.CRITICAL,
        # HIGH - Should be reviewed
        "identity_attack": ValidationSeverity.HIGH,
        "insult": ValidationSeverity.HIGH,
        # MEDIUM - Warning
        "obscene": ValidationSeverity.MEDIUM,
        "toxicity": ValidationSeverity.MEDIUM,
        # Additional categories (if available in model)
        "sexual_explicit": ValidationSeverity.HIGH,
    }

    def __init__(self, model_type: str = "original", threshold: float = 0.5):
        """
        Initialize Detoxify-based toxic content detector

        Args:
            model_type: 'original', 'unbiased', or 'multilingual'
            threshold: Minimum confidence score (0.0-1.0)
        """
        if not DETOXIFY_AVAILABLE:
            raise ImportError(
                "Detoxify is not installed. Install with: pip install detoxify"
            )

        self.threshold = threshold
        self.model_type = model_type

        try:
            # Initialize Detoxify model
            self.model = DetoxifyModel(model_type)

            logger.info(
                f"ToxicContentDetectorML initialized - "
                f"Model: {model_type}, "
                f"Threshold: {threshold}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize Detoxify: {e}")
            raise

    def detect(self, text: str) -> List[ValidationIssue]:
        """
        Detect toxic content in text using Detoxify's ML model

        Args:
            text: Text to analyze

        Returns:
            List of ValidationIssue objects
        """
        if not text or not text.strip():
            return []

        try:
            # Analyze text with Detoxify
            results = self.model.predict(text)

            # Convert results to ValidationIssue objects
            issues = []
            for category, score in results.items():
                if score > self.threshold:
                    # Determine severity
                    severity = self.CATEGORY_SEVERITY_MAP.get(
                        category, ValidationSeverity.MEDIUM
                    )

                    # Create issue
                    issue = ValidationIssue(
                        issue_type=f"TOXIC_{category.upper()}",
                        severity=severity,
                        description=f"{category} detected (confidence: {score:.2f})",
                        matched_text=None,  # Don't expose toxic content
                        position=None,
                        metadata={
                            "confidence": score,
                            "model": self.model_type,
                            "threshold": self.threshold,
                        },
                    )
                    issues.append(issue)

            if issues:
                logger.debug(
                    f"Detoxify detected {len(issues)} toxic content instance(s)"
                )

            return issues

        except Exception as e:
            logger.error(f"Detoxify detection failed: {e}")
            return []

    def detect_by_category(self, text: str, category: str) -> List[ValidationIssue]:
        """
        Detect specific toxicity category

        Args:
            text: Text to analyze
            category: Specific category (e.g., "toxicity", "insult")

        Returns:
            List of ValidationIssue objects for that category
        """
        all_issues = self.detect(text)
        return [
            issue
            for issue in all_issues
            if issue.issue_type == f"TOXIC_{category.upper()}"
        ]

    def has_toxic_content(
        self, text: str, min_severity: ValidationSeverity = ValidationSeverity.LOW
    ) -> bool:
        """
        Check if text contains toxic content above minimum severity

        Args:
            text: Text to check
            min_severity: Minimum severity level

        Returns:
            True if toxic content found above threshold
        """
        issues = self.detect(text)
        return any(issue.severity.value >= min_severity.value for issue in issues)

    def get_toxicity_score(self, text: str) -> float:
        """
        Get overall toxicity score

        Args:
            text: Text to analyze

        Returns:
            Toxicity score (0.0-1.0)
        """
        try:
            results = self.model.predict(text)
            # Return the main toxicity score
            return results.get("toxicity", 0.0)
        except Exception as e:
            logger.error(f"Failed to get toxicity score: {e}")
            return 0.0

    def get_detailed_scores(self, text: str) -> Dict[str, float]:
        """
        Get detailed scores for all categories

        Args:
            text: Text to analyze

        Returns:
            Dictionary mapping categories to scores
        """
        try:
            return self.model.predict(text)
        except Exception as e:
            logger.error(f"Failed to get detailed scores: {e}")
            return {}

    def get_category_counts(self, text: str) -> Dict[str, int]:
        """
        Get count of each toxic category found

        Args:
            text: Text to analyze

        Returns:
            Dictionary mapping category types to counts
        """
        issues = self.detect(text)
        counts = {}
        for issue in issues:
            category = issue.issue_type.replace("TOXIC_", "")
            counts[category] = counts.get(category, 0) + 1
        return counts

    def is_safe_for_medical_context(self, text: str) -> bool:
        """
        Check if text is safe for medical context
        Uses lower threshold for medical terms

        Args:
            text: Text to check

        Returns:
            True if safe for medical use
        """
        # Medical context might use words like "sexual", "kill" (bacteria)
        # Use higher threshold to reduce false positives
        medical_threshold = 0.7  # Higher than default 0.5

        try:
            results = self.model.predict(text)

            # Check critical categories with normal threshold
            critical_categories = ["severe_toxicity", "threat", "identity_attack"]
            for category in critical_categories:
                if results.get(category, 0) > self.threshold:
                    return False

            # Check other categories with higher threshold
            other_categories = ["toxicity", "obscene", "insult"]
            for category in other_categories:
                if results.get(category, 0) > medical_threshold:
                    return False

            return True

        except Exception as e:
            logger.error(f"Medical context check failed: {e}")
            return True  # Fail open for medical context

    def filter_toxic_content(self, text: str, replacement: str = "[FILTERED]") -> str:
        """
        Filter toxic content from text

        Note: Detoxify doesn't provide word-level detection,
        so this returns the full text or replacement

        Args:
            text: Text to filter
            replacement: Replacement text if toxic

        Returns:
            Original text or replacement if toxic
        """
        if self.has_toxic_content(text):
            return replacement
        return text

    def get_supported_categories(self) -> List[str]:
        """Get list of all supported toxicity categories"""
        return list(self.CATEGORY_SEVERITY_MAP.keys())


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if not DETOXIFY_AVAILABLE:
        print("❌ Detoxify is not installed!")
        print("\nInstall with:")
        print("  pip install detoxify")
        exit(1)

    print("\n" + "=" * 80)
    print("DETOXIFY TOXIC CONTENT DETECTOR TEST")
    print("=" * 80 + "\n")

    try:
        detector = ToxicContentDetectorML(model_type="original", threshold=0.5)

        # Test cases
        test_cases = [
            # Medical context (should have low false positives)
            "Sexual dysfunction is a common symptom of diabetes",
            "This medication can kill harmful bacteria",
            "The patient experienced a severe asthma assault",
            "This damn disease is hard to manage",
            # Actually toxic content
            "You're a stupid idiot and I hate you",
            "This f*cking system sucks",
            "I'm going to kill you",
            # Clean content
            "Diabetes is managed through diet, exercise, and medication",
        ]

        for i, text in enumerate(test_cases, 1):
            print(f"\nTest {i}: {text}")
            print("-" * 80)

            # Get detailed scores
            scores = detector.get_detailed_scores(text)

            print("Toxicity Scores:")
            for category, score in sorted(
                scores.items(), key=lambda x: x[1], reverse=True
            ):
                emoji = "🔴" if score > 0.5 else "🟡" if score > 0.3 else "🟢"
                print(f"  {emoji} {category:20} {score:.3f}")

            # Get issues
            issues = detector.detect(text)

            if issues:
                print(f"\n⚠️  Found {len(issues)} issue(s):")
                for issue in issues:
                    print(f"  - {issue}")
            else:
                print("\n✅ No toxic content detected")

            # Medical context check
            is_safe = detector.is_safe_for_medical_context(text)
            print(f"\nSafe for medical context: {'YES ✓' if is_safe else 'NO ✗'}")

        # Show supported categories
        print("\n" + "=" * 80)
        print("SUPPORTED CATEGORIES")
        print("=" * 80)
        categories = detector.get_supported_categories()
        print(f"Total: {len(categories)} categories")
        for category in categories:
            severity = detector.CATEGORY_SEVERITY_MAP.get(category, "N/A")
            print(f"  • {category:25} - {severity}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
