"""
Content Validator
Main validator that orchestrates PII and toxic content detection
Supports both regex-based and ML-based detection for PII and toxic content
"""

import logging
from typing import List, Tuple, Dict, Optional

# Import from parent src package
from ..utils.logger import get_logger

from .pii_detector import PIIDetector
from .toxic_detector import ToxicContentDetector
from .config import (
    ValidationIssue,
    ValidationSeverity,
    ValidationConfig,
    PIIDetectionMode,
    ToxicDetectionMode,
)

logger = get_logger(__name__)


class ContentValidator:
    """
    Main content validator that orchestrates PII and toxic content detection
    Supports multiple detection modes for both PII and toxic content
    """

    def __init__(self, config: Optional[ValidationConfig] = None):
        """
        Initialize the content validator

        Args:
            config: ValidationConfig object, uses defaults if not provided
        """
        self.config = config or ValidationConfig()

        # Initialize PII detector based on mode
        self.pii_detector_regex = None
        self.pii_detector_presidio = None

        if self.config.enable_pii_detection:
            mode = self.config.pii_detection_mode

            if mode in [PIIDetectionMode.REGEX, PIIDetectionMode.HYBRID]:
                # Initialize regex-based detector
                self.pii_detector_regex = PIIDetector(
                    custom_patterns=self.config.custom_pii_patterns
                )
                logger.info("Initialized regex-based PII detector")

            if mode in [PIIDetectionMode.PRESIDIO, PIIDetectionMode.HYBRID]:
                # Try to initialize Presidio detector
                try:
                    from .pii_detector_presidio import PIIDetectorPresidio

                    self.pii_detector_presidio = PIIDetectorPresidio(
                        language=self.config.presidio_language,
                        score_threshold=self.config.presidio_score_threshold,
                    )
                    logger.info("Initialized Presidio PII detector")
                except ImportError as e:
                    logger.warning(
                        f"Presidio not available: {e}. "
                        "Falling back to regex-based detection. "
                        "Install with: pip install presidio-analyzer presidio-anonymizer"
                    )
                    # Fallback to regex if Presidio not available
                    if not self.pii_detector_regex:
                        self.pii_detector_regex = PIIDetector(
                            custom_patterns=self.config.custom_pii_patterns
                        )
                except Exception as e:
                    logger.error(f"Failed to initialize Presidio: {e}")
                    # Fallback to regex
                    if not self.pii_detector_regex:
                        self.pii_detector_regex = PIIDetector(
                            custom_patterns=self.config.custom_pii_patterns
                        )

        # Initialize toxic content detector based on mode
        self.toxic_detector_wordlist = None
        self.toxic_detector_ml = None

        if self.config.enable_toxic_detection:
            mode = self.config.toxic_detection_mode

            if mode in [ToxicDetectionMode.WORDLIST, ToxicDetectionMode.HYBRID]:
                # Initialize word-list based detector
                self.toxic_detector_wordlist = ToxicContentDetector(
                    custom_words=self.config.custom_toxic_words
                )
                logger.info("Initialized word-list toxic detector")

            if mode in [ToxicDetectionMode.ML, ToxicDetectionMode.HYBRID]:
                # Try to initialize Detoxify detector
                try:
                    from .toxic_detector_ml import ToxicContentDetectorML

                    self.toxic_detector_ml = ToxicContentDetectorML(
                        model_type=self.config.detoxify_model_type,
                        threshold=self.config.detoxify_threshold,
                    )
                    logger.info("Initialized Detoxify toxic detector")
                except ImportError as e:
                    logger.warning(
                        f"Detoxify not available: {e}. "
                        "Falling back to word-list detection. "
                        "Install with: pip install detoxify"
                    )
                    # Fallback to word-list if Detoxify not available
                    if not self.toxic_detector_wordlist:
                        self.toxic_detector_wordlist = ToxicContentDetector(
                            custom_words=self.config.custom_toxic_words
                        )
                except Exception as e:
                    logger.error(f"Failed to initialize Detoxify: {e}")
                    # Fallback to word-list
                    if not self.toxic_detector_wordlist:
                        self.toxic_detector_wordlist = ToxicContentDetector(
                            custom_words=self.config.custom_toxic_words
                        )

        logger.info(
            f"ContentValidator initialized - "
            f"PII Mode: {self.config.pii_detection_mode.value if self.config.enable_pii_detection else 'disabled'}, "
            f"Toxic Mode: {self.config.toxic_detection_mode.value if self.config.enable_toxic_detection else 'disabled'}"
        )

    def validate(self, text: str) -> Tuple[bool, List[ValidationIssue]]:
        """
        Validate text for PII and toxic content

        Args:
            text: Text to validate

        Returns:
            Tuple of (is_safe, list_of_issues)
            - is_safe: True if content is safe to process, False if blocked
            - list_of_issues: List of all validation issues found
        """
        all_issues = []

        # Run PII detection based on mode
        if self.config.enable_pii_detection:
            pii_issues = []

            # Regex detection
            if self.pii_detector_regex:
                regex_issues = self.pii_detector_regex.detect(text)
                pii_issues.extend(regex_issues)
                if self.config.verbose and regex_issues:
                    logger.debug(
                        f"Regex detector found {len(regex_issues)} PII issue(s)"
                    )

            # Presidio detection
            if self.pii_detector_presidio:
                presidio_issues = self.pii_detector_presidio.detect(text)

                # In HYBRID mode, merge results (remove duplicates)
                if self.config.pii_detection_mode == PIIDetectionMode.HYBRID:
                    # Add only unique Presidio findings
                    for p_issue in presidio_issues:
                        # Check if similar issue already found by regex
                        is_duplicate = any(
                            abs(p_issue.position - r_issue.position) < 5
                            for r_issue in pii_issues
                            if r_issue.position is not None
                            and p_issue.position is not None
                        )
                        if not is_duplicate:
                            pii_issues.append(p_issue)
                else:
                    pii_issues.extend(presidio_issues)

                if self.config.verbose and presidio_issues:
                    logger.debug(
                        f"Presidio detector found {len(presidio_issues)} PII issue(s)"
                    )

            all_issues.extend(pii_issues)

            if self.config.verbose and pii_issues:
                logger.debug(f"Total PII issues: {len(pii_issues)}")

        # Run toxic content detection based on mode
        if self.config.enable_toxic_detection:
            toxic_issues = []

            # Word-list detection
            if self.toxic_detector_wordlist:
                wordlist_issues = self.toxic_detector_wordlist.detect(text)
                toxic_issues.extend(wordlist_issues)
                if self.config.verbose and wordlist_issues:
                    logger.debug(
                        f"Word-list detector found {len(wordlist_issues)} toxic issue(s)"
                    )

            # ML detection (Detoxify)
            if self.toxic_detector_ml:
                ml_issues = self.toxic_detector_ml.detect(text)

                # In HYBRID mode, merge results (ML takes precedence for accuracy)
                if self.config.toxic_detection_mode == ToxicDetectionMode.HYBRID:
                    # If ML detector says it's safe, trust it (reduces false positives)
                    if not ml_issues:
                        # ML says clean, remove word-list false positives
                        toxic_issues = []
                    else:
                        # ML found issues, use ML results (more accurate)
                        toxic_issues = ml_issues
                else:
                    toxic_issues.extend(ml_issues)

                if self.config.verbose and ml_issues:
                    logger.debug(f"ML detector found {len(ml_issues)} toxic issue(s)")

            all_issues.extend(toxic_issues)

            if self.config.verbose and toxic_issues:
                logger.debug(f"Total toxic issues: {len(toxic_issues)}")

        # Determine if content should be blocked
        is_safe = self._evaluate_safety(all_issues)

        # Log summary
        if all_issues and self.config.log_issues:
            logger.warning(
                f"Validation found {len(all_issues)} issue(s) - "
                f"Safe to process: {is_safe}"
            )
            if self.config.verbose:
                for issue in all_issues:
                    logger.debug(f"  - {issue}")
        else:
            if self.config.verbose:
                logger.debug("Validation passed - no issues found")

        return is_safe, all_issues

    def validate_batch(
        self, texts: List[str]
    ) -> List[Tuple[bool, List[ValidationIssue]]]:
        """
        Validate multiple texts

        Args:
            texts: List of texts to validate

        Returns:
            List of (is_safe, issues) tuples for each text
        """
        results = []
        for i, text in enumerate(texts):
            if self.config.verbose:
                logger.debug(f"Validating text {i + 1}/{len(texts)}")
            results.append(self.validate(text))

        return results

    def _evaluate_safety(self, issues: List[ValidationIssue]) -> bool:
        """
        Evaluate if content is safe based on issues found

        Args:
            issues: List of validation issues

        Returns:
            True if safe to process, False if should be blocked
        """
        if not issues:
            return True

        # Separate PII and toxic issues
        pii_issues = [i for i in issues if i.issue_type.startswith("PII_")]
        toxic_issues = [i for i in issues if i.issue_type.startswith("TOXIC_")]

        # Check PII blocking rules
        if self.config.enable_pii_detection and pii_issues:
            if self.config.pii_block_on_critical:
                critical_pii = [
                    i for i in pii_issues if i.severity == ValidationSeverity.CRITICAL
                ]
                if critical_pii:
                    logger.error(
                        f"Content blocked due to {len(critical_pii)} "
                        f"CRITICAL PII issue(s)"
                    )
                    return False

            if self.config.pii_block_on_high:
                high_pii = [
                    i for i in pii_issues if i.severity == ValidationSeverity.HIGH
                ]
                if high_pii:
                    logger.warning(
                        f"Content blocked due to {len(high_pii)} "
                        f"HIGH severity PII issue(s)"
                    )
                    return False

        # Check toxic content blocking rules
        if self.config.enable_toxic_detection and toxic_issues:
            if self.config.toxic_block_on_critical:
                critical_toxic = [
                    i for i in toxic_issues if i.severity == ValidationSeverity.CRITICAL
                ]
                if critical_toxic:
                    logger.error(
                        f"Content blocked due to {len(critical_toxic)} "
                        f"CRITICAL toxic content issue(s)"
                    )
                    return False

            if self.config.toxic_block_on_high:
                high_toxic = [
                    i for i in toxic_issues if i.severity == ValidationSeverity.HIGH
                ]
                if high_toxic:
                    logger.warning(
                        f"Content blocked due to {len(high_toxic)} "
                        f"HIGH severity toxic content issue(s)"
                    )
                    return False

        return True

    def get_validation_summary(self, issues: List[ValidationIssue]) -> Dict:
        """
        Get a summary of validation issues

        Args:
            issues: List of validation issues

        Returns:
            Dictionary with summary statistics
        """
        summary = {
            "total_issues": len(issues),
            "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "by_type": {},
            "pii_count": 0,
            "toxic_count": 0,
        }

        for issue in issues:
            # Count by severity
            summary["by_severity"][issue.severity.value] += 1

            # Count by type
            if issue.issue_type not in summary["by_type"]:
                summary["by_type"][issue.issue_type] = 0
            summary["by_type"][issue.issue_type] += 1

            # Count PII vs Toxic
            if issue.issue_type.startswith("PII_"):
                summary["pii_count"] += 1
            elif issue.issue_type.startswith("TOXIC_"):
                summary["toxic_count"] += 1

        return summary

    def sanitize_content(
        self, text: str, redact_pii: bool = True, filter_toxic: bool = True
    ) -> str:
        """
        Sanitize content by redacting PII and filtering toxic content

        Args:
            text: Text to sanitize
            redact_pii: Whether to redact PII
            filter_toxic: Whether to filter toxic content

        Returns:
            Sanitized text
        """
        sanitized = text

        if redact_pii and self.config.enable_pii_detection:
            # Use Presidio for redaction if available (more accurate)
            if self.pii_detector_presidio:
                sanitized = self.pii_detector_presidio.redact_pii(sanitized)
            elif self.pii_detector_regex:
                sanitized = self.pii_detector_regex.redact_pii(sanitized)

        if filter_toxic and self.config.enable_toxic_detection:
            # Use ML detector for filtering if available (more accurate)
            if self.toxic_detector_ml:
                sanitized = self.toxic_detector_ml.filter_toxic_content(sanitized)
            elif self.toxic_detector_wordlist:
                sanitized = self.toxic_detector_wordlist.filter_toxic_content(sanitized)

        return sanitized


# Example usage
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Test cases
    test_texts = [
        "This is a clean medical text about diabetes treatment.",
        "Patient John Doe, email: john.doe@email.com, phone: 555-123-4567",
        "SSN: 123-45-6789, Credit Card: 1234-5678-9012-3456",
        "This text contains profanity: damn and shit",
        "Medical Record: MRN A123456, DOB: 01/15/1980",
        "You're a stupid idiot! I hate you!",
    ]

    # Initialize validator with custom config
    config = ValidationConfig(
        enable_pii_detection=True,
        enable_toxic_detection=True,
        pii_block_on_critical=True,
        pii_block_on_high=False,
        toxic_block_on_critical=True,
        toxic_block_on_high=False,
        log_issues=True,
        verbose=True,
    )

    validator = ContentValidator(config)

    print("\n" + "=" * 80)
    print("CONTENT VALIDATION TEST")
    print("=" * 80 + "\n")

    for i, text in enumerate(test_texts, 1):
        print(f"\nTest {i}: {text[:60]}...")
        print("-" * 80)

        is_safe, issues = validator.validate(text)

        if issues:
            print(f"❌ Issues found: {len(issues)}")
            for issue in issues:
                print(f"  - {issue}")

            summary = validator.get_validation_summary(issues)
            print("\nSummary:")
            print(f"  PII Issues: {summary['pii_count']}")
            print(f"  Toxic Issues: {summary['toxic_count']}")

            print(f"\nSanitized: {validator.sanitize_content(text)}")
        else:
            print("✅ No issues found")

        print(f"Safe to process: {'YES ✓' if is_safe else 'NO ✗'}")
