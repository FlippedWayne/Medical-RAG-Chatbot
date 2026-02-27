"""
NER-based Entity Detector using spaCy
Educational module to demonstrate NLP/NER benefits for entity detection

This is a SEPARATE module that doesn't impact existing detectors.
Use it to learn and compare NER vs pattern-based approaches.
"""

import logging
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from enum import Enum

try:
    import spacy
    from spacy.tokens import Doc

    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

from .config import ValidationIssue, ValidationSeverity

logger = logging.getLogger(__name__)


class EntityType(Enum):
    """Entity types detected by NER"""

    # Standard spaCy entities
    PERSON = "PERSON"
    ORGANIZATION = "ORG"
    LOCATION = "GPE"  # Geo-Political Entity
    DATE = "DATE"
    TIME = "TIME"
    MONEY = "MONEY"
    CARDINAL = "CARDINAL"  # Numbers

    # Medical entities (if using medical models)
    DISEASE = "DISEASE"
    MEDICATION = "MEDICATION"
    SYMPTOM = "SYMPTOM"
    PROCEDURE = "PROCEDURE"


@dataclass
class Entity:
    """Represents a detected entity"""

    text: str
    label: str
    start: int
    end: int
    confidence: float = 1.0

    def __str__(self):
        return f"{self.text} ({self.label}) [{self.start}:{self.end}] conf={self.confidence:.2f}"


class NERDetector:
    """
    NER-based entity detector using spaCy

    Educational module to demonstrate:
    - How NER works
    - Benefits over pattern matching
    - Context-aware entity detection
    - Medical entity recognition
    """

    # Map entity types to PII severity
    ENTITY_SEVERITY_MAP = {
        "PERSON": ValidationSeverity.HIGH,
        "ORG": ValidationSeverity.MEDIUM,
        "GPE": ValidationSeverity.MEDIUM,
        "DATE": ValidationSeverity.MEDIUM,
        "MONEY": ValidationSeverity.LOW,
        "CARDINAL": ValidationSeverity.LOW,
        # Medical entities
        "DISEASE": ValidationSeverity.MEDIUM,
        "MEDICATION": ValidationSeverity.MEDIUM,
        "SYMPTOM": ValidationSeverity.LOW,
        "PROCEDURE": ValidationSeverity.MEDIUM,
    }

    def __init__(
        self,
        model_name: str = "en_core_web_sm",
        detect_persons: bool = True,
        detect_organizations: bool = True,
        detect_locations: bool = True,
        detect_dates: bool = True,
    ):
        """
        Initialize NER detector

        Args:
            model_name: spaCy model to use
                - en_core_web_sm: Small general model (default)
                - en_core_web_md: Medium general model
                - en_core_web_lg: Large general model
                - en_core_sci_sm: Scientific/medical model (requires scispacy)
            detect_persons: Detect person names
            detect_organizations: Detect organization names
            detect_locations: Detect locations
            detect_dates: Detect dates
        """
        if not SPACY_AVAILABLE:
            raise ImportError(
                "spaCy is not installed. Install with: "
                "pip install spacy && python -m spacy download en_core_web_sm"
            )

        self.model_name = model_name
        self.detect_persons = detect_persons
        self.detect_organizations = detect_organizations
        self.detect_locations = detect_locations
        self.detect_dates = detect_dates

        try:
            # Load spaCy model
            self.nlp = spacy.load(model_name)

            logger.info(
                f"NERDetector initialized - "
                f"Model: {model_name}, "
                f"Entities: PERSON={detect_persons}, ORG={detect_organizations}, "
                f"LOC={detect_locations}, DATE={detect_dates}"
            )

        except OSError as e:
            logger.error(f"Failed to load spaCy model '{model_name}': {e}")
            logger.info(f"Download with: python -m spacy download {model_name}")
            raise

    def detect_entities(self, text: str) -> List[Entity]:
        """
        Detect all entities in text using NER

        Args:
            text: Text to analyze

        Returns:
            List of Entity objects
        """
        if not text or not text.strip():
            return []

        try:
            # Process text with spaCy NER
            doc = self.nlp(text)

            entities = []
            for ent in doc.ents:
                # Filter based on configuration
                if not self._should_detect_entity(ent.label_):
                    continue

                entity = Entity(
                    text=ent.text,
                    label=ent.label_,
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=1.0,  # spaCy doesn't provide confidence by default
                )
                entities.append(entity)

            if entities:
                logger.debug(f"NER detected {len(entities)} entity/entities")

            return entities

        except Exception as e:
            logger.error(f"NER detection failed: {e}")
            return []

    def detect_pii_entities(self, text: str) -> List[ValidationIssue]:
        """
        Detect PII entities and convert to ValidationIssue format

        Args:
            text: Text to analyze

        Returns:
            List of ValidationIssue objects
        """
        entities = self.detect_entities(text)
        issues = []

        for entity in entities:
            # Only flag PII-relevant entities
            if entity.label_ in ["PERSON", "ORG", "GPE", "DATE"]:
                severity = self.ENTITY_SEVERITY_MAP.get(
                    entity.label_, ValidationSeverity.MEDIUM
                )

                issue = ValidationIssue(
                    issue_type=f"NER_{entity.label_}",
                    severity=severity,
                    description=f"{entity.label_} entity detected via NER",
                    matched_text=self._mask_entity(entity.text),
                    position=entity.start,
                    metadata={
                        "entity_type": entity.label_,
                        "confidence": entity.confidence,
                        "detector": "spacy_ner",
                    },
                )
                issues.append(issue)

        return issues

    def get_entity_counts(self, text: str) -> Dict[str, int]:
        """
        Get count of each entity type

        Args:
            text: Text to analyze

        Returns:
            Dictionary mapping entity types to counts
        """
        entities = self.detect_entities(text)
        counts = {}
        for entity in entities:
            counts[entity.label] = counts.get(entity.label, 0) + 1
        return counts

    def get_persons(self, text: str) -> List[str]:
        """Get all person names detected"""
        entities = self.detect_entities(text)
        return [e.text for e in entities if e.label == "PERSON"]

    def get_organizations(self, text: str) -> List[str]:
        """Get all organization names detected"""
        entities = self.detect_entities(text)
        return [e.text for e in entities if e.label == "ORG"]

    def get_locations(self, text: str) -> List[str]:
        """Get all locations detected"""
        entities = self.detect_entities(text)
        return [e.text for e in entities if e.label == "GPE"]

    def redact_entities(
        self,
        text: str,
        entity_types: Optional[Set[str]] = None,
        replacement: str = "[REDACTED]",
    ) -> str:
        """
        Redact specific entity types from text

        Args:
            text: Text to redact
            entity_types: Set of entity types to redact (None = all)
            replacement: Replacement text

        Returns:
            Text with entities redacted
        """
        entities = self.detect_entities(text)

        # Filter by entity types if specified
        if entity_types:
            entities = [e for e in entities if e.label in entity_types]

        # Sort by position (reverse order to maintain indices)
        entities.sort(key=lambda e: e.start, reverse=True)

        # Redact entities
        redacted = text
        for entity in entities:
            redacted = redacted[: entity.start] + replacement + redacted[entity.end :]

        return redacted

    def anonymize_with_labels(self, text: str) -> str:
        """
        Replace entities with their labels

        Example: "Dr. Sarah Johnson works at Memorial Hospital"
                 → "Dr. [PERSON] works at [ORG]"

        Args:
            text: Text to anonymize

        Returns:
            Text with entities replaced by labels
        """
        entities = self.detect_entities(text)
        entities.sort(key=lambda e: e.start, reverse=True)

        anonymized = text
        for entity in entities:
            label_text = f"[{entity.label}]"
            anonymized = (
                anonymized[: entity.start] + label_text + anonymized[entity.end :]
            )

        return anonymized

    def compare_with_patterns(self, text: str) -> Dict:
        """
        Compare NER detection with pattern-based detection
        Educational function to show differences

        Args:
            text: Text to analyze

        Returns:
            Dictionary with comparison results
        """
        import re

        # NER detection
        ner_entities = self.detect_entities(text)
        ner_persons = [e.text for e in ner_entities if e.label == "PERSON"]

        # Pattern-based detection (simple)
        # This is what regex would do - just look for capitalized words
        pattern_persons = re.findall(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", text)

        return {
            "ner_detected": ner_persons,
            "pattern_detected": pattern_persons,
            "ner_only": list(set(ner_persons) - set(pattern_persons)),
            "pattern_only": list(set(pattern_persons) - set(ner_persons)),
            "both": list(set(ner_persons) & set(pattern_persons)),
        }

    def _should_detect_entity(self, label: str) -> bool:
        """Check if entity type should be detected based on config"""
        if label == "PERSON" and not self.detect_persons:
            return False
        if label == "ORG" and not self.detect_organizations:
            return False
        if label == "GPE" and not self.detect_locations:
            return False
        if label == "DATE" and not self.detect_dates:
            return False
        return True

    @staticmethod
    def _mask_entity(text: str, show_chars: int = 2) -> str:
        """Mask entity text for logging"""
        if len(text) <= show_chars * 2:
            return "*" * len(text)
        return f"{text[:show_chars]}***{text[-show_chars:]}"

    def get_supported_entities(self) -> List[str]:
        """Get list of all entity types supported by the model"""
        return list(self.nlp.pipe_labels.get("ner", []))


# Example usage and educational demonstrations
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if not SPACY_AVAILABLE:
        print("❌ spaCy is not installed!")
        print("\nInstall with:")
        print("  pip install spacy")
        print("  python -m spacy download en_core_web_sm")
        exit(1)

    print("\n" + "=" * 80)
    print("NER-BASED ENTITY DETECTION DEMONSTRATION")
    print("=" * 80 + "\n")

    try:
        detector = NERDetector()

        # Educational test cases
        test_cases = [
            {
                "name": "Medical Context with Names",
                "text": "Dr. Sarah Johnson treated patient Michael Smith at Memorial Hospital in Boston.",
            },
            {
                "name": "Medical Information",
                "text": "The patient was diagnosed with type 2 diabetes and prescribed metformin 500mg twice daily.",
            },
            {
                "name": "Appointment Details",
                "text": "Patient John Doe has an appointment on January 15, 2024 at Cleveland Clinic.",
            },
            {
                "name": "Complex Medical Case",
                "text": "Dr. Robert Martinez from Mayo Clinic recommended surgery for the patient's condition.",
            },
        ]

        for i, test in enumerate(test_cases, 1):
            print(f"\n{'=' * 80}")
            print(f"TEST {i}: {test['name']}")
            print(f"{'=' * 80}")
            print(f"Text: {test['text']}\n")

            # Detect entities
            entities = detector.detect_entities(test["text"])

            if entities:
                print(f"✅ NER detected {len(entities)} entity/entities:\n")
                for entity in entities:
                    print(f"  • {entity}")

                # Show entity counts
                counts = detector.get_entity_counts(test["text"])
                print("\nEntity Counts:")
                for entity_type, count in counts.items():
                    print(f"  - {entity_type}: {count}")

                # Show redacted version
                print("\nRedacted (all entities):")
                print(f"  {detector.redact_entities(test['text'])}")

                # Show anonymized version
                print("\nAnonymized (with labels):")
                print(f"  {detector.anonymize_with_labels(test['text'])}")

                # Show redacted (persons only)
                print("\nRedacted (persons only):")
                print(
                    f"  {detector.redact_entities(test['text'], entity_types={'PERSON'})}"
                )

            else:
                print("✅ No entities detected")

            # Compare with pattern matching
            if "Dr." in test["text"] or "patient" in test["text"]:
                print(f"\n{'─' * 80}")
                print("NER vs Pattern Matching Comparison:")
                print(f"{'─' * 80}")
                comparison = detector.compare_with_patterns(test["text"])
                print(f"  NER detected: {comparison['ner_detected']}")
                print(f"  Pattern detected: {comparison['pattern_detected']}")
                print(f"  NER only (missed by patterns): {comparison['ner_only']}")
                print(f"  Pattern only (false positives): {comparison['pattern_only']}")

        # Show supported entities
        print("\n" + "=" * 80)
        print("SUPPORTED ENTITY TYPES")
        print("=" * 80)
        entities = detector.get_supported_entities()
        print(f"Total: {len(entities)} entity types\n")
        for entity in sorted(entities):
            severity = detector.ENTITY_SEVERITY_MAP.get(entity, "N/A")
            print(f"  • {entity:20} - {severity}")

        # Educational summary
        print("\n" + "=" * 80)
        print("EDUCATIONAL SUMMARY: NER vs Pattern Matching")
        print("=" * 80)
        print("""
NER (Named Entity Recognition) Benefits:
✅ Context-aware: Understands "Dr. Smith" is a person
✅ Handles variations: "Sarah Johnson" vs "Dr. Sarah Johnson"
✅ Reduces false positives: Knows "Memorial Hospital" is organization
✅ Detects complex entities: Multi-word names, titles
✅ Language understanding: Uses ML models trained on real text

Pattern Matching Limitations:
❌ No context: Just looks for patterns like "A-Z a-z A-Z a-z"
❌ False positives: "New York" detected as person name
❌ Misses variations: Doesn't understand titles (Dr., Prof.)
❌ Rigid: Can't adapt to new patterns
❌ No semantic understanding: Just string matching

When to Use NER:
• Detecting person names in medical records
• Identifying organizations and locations
• Understanding context (Dr. vs patient)
• Reducing false positives
• Production medical applications

When to Use Patterns:
• Structured data (SSN: 123-45-6789)
• Known formats (emails, phone numbers)
• Fast detection needed
• Simple use cases
• Development/testing
        """)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
