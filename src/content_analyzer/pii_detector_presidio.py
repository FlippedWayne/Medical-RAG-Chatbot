"""
Enhanced PII Detector using Microsoft Presidio
Provides ML-based, context-aware PII detection with higher accuracy
"""

import logging
from typing import List, Dict, Optional

try:
    from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_anonymizer import AnonymizerEngine
    from presidio_anonymizer.entities import OperatorConfig

    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False

from .config import ValidationIssue, ValidationSeverity

logger = logging.getLogger(__name__)


class PIIDetectorPresidio:
    """
    Enhanced PII detector using Microsoft Presidio

    Features:
    - ML-based entity recognition
    - Context-aware detection
    - 50+ entity types supported
    - Multi-language support
    - Lower false positives
    - Confidence scores
    """

    # Map Presidio entity types to severity levels
    ENTITY_SEVERITY_MAP = {
        # CRITICAL - Must be blocked
        "US_SSN": ValidationSeverity.CRITICAL,
        "CREDIT_CARD": ValidationSeverity.CRITICAL,
        "US_PASSPORT": ValidationSeverity.CRITICAL,
        "US_DRIVER_LICENSE": ValidationSeverity.CRITICAL,
        "MEDICAL_LICENSE": ValidationSeverity.CRITICAL,
        "US_BANK_NUMBER": ValidationSeverity.CRITICAL,
        "CRYPTO": ValidationSeverity.CRITICAL,
        "IBAN_CODE": ValidationSeverity.CRITICAL,
        # HIGH - Should be reviewed
        "EMAIL_ADDRESS": ValidationSeverity.HIGH,
        "PHONE_NUMBER": ValidationSeverity.HIGH,
        "PERSON": ValidationSeverity.HIGH,
        "US_ITIN": ValidationSeverity.HIGH,
        "AU_TFN": ValidationSeverity.HIGH,
        "AU_MEDICARE": ValidationSeverity.HIGH,
        # MEDIUM - Warning
        "LOCATION": ValidationSeverity.MEDIUM,
        "DATE_TIME": ValidationSeverity.MEDIUM,
        "IP_ADDRESS": ValidationSeverity.MEDIUM,
        "URL": ValidationSeverity.MEDIUM,
        "NRP": ValidationSeverity.MEDIUM,  # National Registry of Persons
        # LOW - Informational
        "AGE": ValidationSeverity.LOW,
        "ORGANIZATION": ValidationSeverity.LOW,
    }

    def __init__(
        self,
        language: str = "en",
        entities: Optional[List[str]] = None,
        score_threshold: float = 0.5,
    ):
        """
        Initialize Presidio-based PII detector

        Args:
            language: Language code (default: 'en')
            entities: List of entity types to detect (None = all)
            score_threshold: Minimum confidence score (0.0-1.0)
        """
        if not PRESIDIO_AVAILABLE:
            raise ImportError(
                "Presidio is not installed. Install with: "
                "pip install presidio-analyzer presidio-anonymizer spacy"
            )

        self.language = language
        self.score_threshold = score_threshold

        # Initialize Presidio engines
        try:
            # Set up NLP engine (using spaCy)
            configuration = {
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": language, "model_name": "en_core_web_sm"}],
            }

            provider = NlpEngineProvider(nlp_configuration=configuration)
            nlp_engine = provider.create_engine()

            # Initialize analyzer with NLP engine
            self.analyzer = AnalyzerEngine(nlp_engine=nlp_engine)
            self.anonymizer = AnonymizerEngine()

            # Set entities to detect
            # NOTE: PERSON is intentionally excluded — spaCy's en_core_web_sm model
            # frequently misclassifies capitalized medical terms (e.g., "Insulin",
            # "Pancreas", "Beta cells") as person names, causing false positives
            # that block legitimate medical answers.
            self.entities = entities or [
                "EMAIL_ADDRESS",
                "PHONE_NUMBER",
                "CREDIT_CARD",
                "US_SSN",
                "MEDICAL_LICENSE",
                "IP_ADDRESS",
                "US_PASSPORT",
                "US_DRIVER_LICENSE",
                "US_BANK_NUMBER",
                "CRYPTO",
                "IBAN_CODE",
                "US_ITIN",
            ]

            logger.info(
                f"PIIDetectorPresidio initialized - "
                f"Language: {language}, "
                f"Entities: {len(self.entities)}, "
                f"Threshold: {score_threshold}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize Presidio: {e}")
            logger.warning(
                "Make sure spaCy model is installed: "
                "python -m spacy download en_core_web_sm"
            )
            raise

    def detect(self, text: str) -> List[ValidationIssue]:
        """
        Detect PII in text using Presidio's ML models

        Args:
            text: Text to analyze

        Returns:
            List of ValidationIssue objects
        """
        if not text or not text.strip():
            return []

        try:
            # Analyze text with Presidio
            results = self.analyzer.analyze(
                text=text,
                language=self.language,
                entities=self.entities,
                score_threshold=self.score_threshold,
            )

            # Convert Presidio results to ValidationIssue
            issues = []
            for result in results:
                # Get matched text
                matched_text = text[result.start : result.end]

                # Determine severity
                severity = self.ENTITY_SEVERITY_MAP.get(
                    result.entity_type, ValidationSeverity.MEDIUM
                )

                # Create issue
                issue = ValidationIssue(
                    issue_type=f"PII_{result.entity_type}",
                    severity=severity,
                    description=f"{result.entity_type} detected (confidence: {result.score:.2f})",
                    matched_text=self._mask_sensitive_data(matched_text),
                    position=result.start,
                    metadata={
                        "confidence": result.score,
                        "recognizer": result.recognition_metadata.get(
                            "recognizer_name", "unknown"
                        ),
                    },
                )
                issues.append(issue)

            if issues:
                logger.debug(f"Presidio detected {len(issues)} PII instance(s)")

            return issues

        except Exception as e:
            logger.error(f"Presidio detection failed: {e}")
            return []

    def detect_by_type(self, text: str, entity_type: str) -> List[ValidationIssue]:
        """
        Detect specific PII entity type

        Args:
            text: Text to analyze
            entity_type: Specific entity type (e.g., "EMAIL_ADDRESS")

        Returns:
            List of ValidationIssue objects for that type
        """
        all_issues = self.detect(text)
        return [
            issue for issue in all_issues if issue.issue_type == f"PII_{entity_type}"
        ]

    def has_pii(
        self, text: str, min_severity: ValidationSeverity = ValidationSeverity.LOW
    ) -> bool:
        """
        Check if text contains PII above minimum severity

        Args:
            text: Text to check
            min_severity: Minimum severity level

        Returns:
            True if PII found above threshold
        """
        issues = self.detect(text)
        return any(issue.severity.value >= min_severity.value for issue in issues)

    def get_pii_count(self, text: str) -> Dict[str, int]:
        """
        Get count of each PII type detected

        Args:
            text: Text to analyze

        Returns:
            Dictionary mapping entity types to counts
        """
        issues = self.detect(text)
        counts = {}
        for issue in issues:
            entity_type = issue.issue_type.replace("PII_", "")
            counts[entity_type] = counts.get(entity_type, 0) + 1
        return counts

    def redact_pii(self, text: str, redaction_text: str = "[REDACTED]") -> str:
        """
        Redact PII from text using Presidio

        Args:
            text: Text to redact
            redaction_text: Replacement text

        Returns:
            Text with PII redacted
        """
        try:
            # Analyze text
            analyzer_results = self.analyzer.analyze(
                text=text,
                language=self.language,
                entities=self.entities,
                score_threshold=self.score_threshold,
            )

            # Anonymize with custom operator
            anonymized = self.anonymizer.anonymize(
                text=text,
                analyzer_results=analyzer_results,
                operators={
                    "DEFAULT": OperatorConfig("replace", {"new_value": redaction_text})
                },
            )

            return anonymized.text

        except Exception as e:
            logger.error(f"Presidio redaction failed: {e}")
            return text

    def anonymize_with_fake_data(self, text: str) -> str:
        """
        Replace PII with fake but realistic data

        Args:
            text: Text to anonymize

        Returns:
            Text with PII replaced by fake data
        """
        try:
            analyzer_results = self.analyzer.analyze(
                text=text, language=self.language, entities=self.entities
            )

            # Use different operators for different entity types
            operators = {
                "PERSON": OperatorConfig("replace", {"new_value": "John Doe"}),
                "EMAIL_ADDRESS": OperatorConfig(
                    "replace", {"new_value": "user@example.com"}
                ),
                "PHONE_NUMBER": OperatorConfig("replace", {"new_value": "555-0000"}),
                "LOCATION": OperatorConfig("replace", {"new_value": "City, State"}),
                "DEFAULT": OperatorConfig("replace", {"new_value": "[REDACTED]"}),
            }

            anonymized = self.anonymizer.anonymize(
                text=text, analyzer_results=analyzer_results, operators=operators
            )

            return anonymized.text

        except Exception as e:
            logger.error(f"Presidio anonymization failed: {e}")
            return text

    @staticmethod
    def _mask_sensitive_data(text: str, show_chars: int = 2) -> str:
        """
        Mask sensitive data for logging

        Args:
            text: Text to mask
            show_chars: Number of characters to show at start/end

        Returns:
            Masked text
        """
        if len(text) <= show_chars * 2:
            return "*" * len(text)
        return f"{text[:show_chars]}***{text[-show_chars:]}"

    def get_supported_entities(self) -> List[str]:
        """Get list of all supported entity types"""
        return self.analyzer.get_supported_entities(language=self.language)


# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if not PRESIDIO_AVAILABLE:
        print("❌ Presidio is not installed!")
        print("\nInstall with:")
        print("  pip install presidio-analyzer presidio-anonymizer")
        print("  python -m spacy download en_core_web_sm")
        exit(1)

    print("\n" + "=" * 80)
    print("PRESIDIO PII DETECTOR TEST")
    print("=" * 80 + "\n")

    try:
        detector = PIIDetectorPresidio()

        # Test cases
        test_cases = [
            "My email is john.doe@example.com and phone is 555-123-4567",
            "SSN: 123-45-6789, Credit Card: 4532-1234-5678-9010",
            "Dr. Sarah Johnson works at Memorial Hospital in Boston",
            "Patient ID: MRN-987654, DOB: 01/15/1980",
            "Contact me at 192.168.1.1 or visit https://example.com",
        ]

        for i, text in enumerate(test_cases, 1):
            print(f"\nTest {i}: {text}")
            print("-" * 80)

            issues = detector.detect(text)

            if issues:
                print(f"✅ Found {len(issues)} PII instance(s):")
                for issue in issues:
                    print(f"  - {issue}")

                # Show redacted version
                redacted = detector.redact_pii(text)
                print(f"\nRedacted: {redacted}")
            else:
                print("✅ No PII detected")

        # Show supported entities
        print("\n" + "=" * 80)
        print("SUPPORTED ENTITY TYPES")
        print("=" * 80)
        entities = detector.get_supported_entities()
        print(f"Total: {len(entities)} entity types")
        for entity in sorted(entities):
            severity = detector.ENTITY_SEVERITY_MAP.get(entity, "N/A")
            print(f"  • {entity:25} - {severity}")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
