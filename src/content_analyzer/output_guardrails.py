"""
Output Guardrails for LLM Responses
Validates LLM-generated content before showing to users

Run from Content_Analyzer directory:
    python output_guardrails.py
"""

import logging
from typing import List, Tuple
from .config import ValidationIssue, ValidationSeverity
from .pii_detector import PIIDetector
from .toxic_detector import ToxicContentDetector

# LangSmith tracing
try:
    from langsmith import traceable

    LANGSMITH_AVAILABLE = True
except ImportError:
    LANGSMITH_AVAILABLE = False

    # Create a no-op decorator if LangSmith is not available
    def traceable(*args, **kwargs):
        def decorator(func):
            return func

        return decorator


# Optional NER detector (requires spaCy)
try:
    from .ner_detector import NERDetector

    NER_AVAILABLE = True
except ImportError:
    NER_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("NER detector not available (spaCy not installed)")

# Optional Presidio PII detector (requires presidio-analyzer)
try:
    from .pii_detector_presidio import PIIDetectorPresidio

    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning(
        "Presidio PII detector not available (presidio-analyzer not installed)"
    )

logger = logging.getLogger(__name__)


class OutputGuardrails:
    """
    Validates LLM output to ensure:
    1. No PII leakage
    2. No toxic content generation
    3. No hallucinated sensitive information
    4. Appropriate medical disclaimers
    5. Factual accuracy checks
    """

    def __init__(
        self,
        enable_pii_check: bool = True,
        enable_toxic_check: bool = True,
        enable_hallucination_check: bool = True,
        require_medical_disclaimer: bool = True,
        enable_ner_check: bool = True,  # Enable NER-based detection
        enable_presidio_check: bool = True,  # NEW: Enable Presidio-based detection
        block_on_pii: bool = True,
        block_on_toxic: bool = True,
    ):
        """
        Initialize output guardrails

        Args:
            enable_pii_check: Check for PII in LLM output
            enable_toxic_check: Check for toxic content in output
            enable_hallucination_check: Check for hallucinated information
            require_medical_disclaimer: Require medical disclaimer for medical advice
            enable_ner_check: Enable NER-based entity detection (requires spaCy)
            enable_presidio_check: Enable Presidio ML-based PII detection (requires presidio-analyzer)
            block_on_pii: Block output if PII detected
            block_on_toxic: Block output if toxic content detected
        """
        self.enable_pii_check = enable_pii_check
        self.enable_toxic_check = enable_toxic_check
        self.enable_hallucination_check = enable_hallucination_check
        self.require_medical_disclaimer = require_medical_disclaimer
        self.enable_ner_check = enable_ner_check and NER_AVAILABLE
        self.enable_presidio_check = enable_presidio_check and PRESIDIO_AVAILABLE
        self.block_on_pii = block_on_pii
        self.block_on_toxic = block_on_toxic

        # Initialize detectors
        self.pii_detector = PIIDetector()  # Pattern-based (always available)
        self.toxic_detector = ToxicContentDetector()

        # Initialize NER detector if available and enabled
        self.ner_detector = None
        if self.enable_ner_check:
            try:
                self.ner_detector = NERDetector(
                    detect_persons=True,
                    detect_organizations=True,
                    detect_locations=False,  # Optional
                    detect_dates=False,  # Optional
                )
                logger.info("✅ NER detector initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize NER detector: {e}")
                self.enable_ner_check = False
        elif NER_AVAILABLE:
            logger.info("ℹ️ NER detector available but disabled")
        else:
            logger.info("ℹ️ NER detector not available (spaCy not installed)")

        # Initialize Presidio PII detector if available and enabled
        self.presidio_detector = None
        if self.enable_presidio_check:
            try:
                self.presidio_detector = PIIDetectorPresidio(
                    language="en", score_threshold=0.5
                )
                logger.info("✅ Presidio PII detector initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize Presidio detector: {e}")
                self.enable_presidio_check = False
        elif PRESIDIO_AVAILABLE:
            logger.info("ℹ️ Presidio detector available but disabled")
        else:
            logger.info(
                "ℹ️ Presidio detector not available (presidio-analyzer not installed)"
            )

        logger.info(
            f"OutputGuardrails initialized - "
            f"PII: {enable_pii_check}, "
            f"Toxic: {enable_toxic_check}, "
            f"Hallucination: {enable_hallucination_check}, "
            f"NER: {self.enable_ner_check}, "
            f"Presidio: {self.enable_presidio_check}"
        )

    @traceable(
        name="guardrails_validation",
        metadata={
            "component": "output_guardrails",
            "checks": ["pii", "toxic", "hallucination", "medical_disclaimer"],
        },
        tags=["security", "guardrails", "validation"],
    )
    def validate_output(
        self,
        llm_output: str,
        original_query: str = "",
        retrieved_context: List[str] = None,
    ) -> Tuple[bool, List[ValidationIssue], str]:
        """
        Validate LLM output before showing to user

        Args:
            llm_output: The LLM-generated response
            original_query: The user's original query (for context)
            retrieved_context: The context that was sent to LLM

        Returns:
            Tuple of (is_safe, issues, safe_output)
            - is_safe: Whether output is safe to show
            - issues: List of validation issues found
            - safe_output: Sanitized output (if modifications needed)
        """
        all_issues = []
        safe_output = llm_output

        # 1. Check for PII leakage
        if self.enable_pii_check:
            pii_issues = self._check_pii_leakage(llm_output)
            all_issues.extend(pii_issues)

            if pii_issues and self.block_on_pii:
                logger.error(f"LLM output blocked: {len(pii_issues)} PII issue(s)")

        # 2. Check for toxic content
        if self.enable_toxic_check:
            toxic_issues = self._check_toxic_content(llm_output)
            all_issues.extend(toxic_issues)

            if toxic_issues and self.block_on_toxic:
                logger.error(f"LLM output blocked: {len(toxic_issues)} toxic issue(s)")

        # 3. Check for hallucinated information
        if self.enable_hallucination_check and retrieved_context:
            hallucination_issues = self._check_hallucinations(
                llm_output, retrieved_context
            )
            all_issues.extend(hallucination_issues)

        # 4. Check for medical advice without disclaimer
        if self.require_medical_disclaimer:
            disclaimer_issues = self._check_medical_disclaimer(
                llm_output, original_query
            )
            all_issues.extend(disclaimer_issues)

            # Add disclaimer if needed
            if disclaimer_issues:
                safe_output = self._add_medical_disclaimer(llm_output)

        # Determine if output is safe
        is_safe = self._evaluate_output_safety(all_issues)

        # Log summary
        if all_issues:
            logger.warning(
                f"Output validation found {len(all_issues)} issue(s) - "
                f"Safe to show: {is_safe}"
            )
        else:
            logger.debug("Output validation passed")

        return is_safe, all_issues, safe_output

    def _check_pii_leakage(self, output: str) -> List[ValidationIssue]:
        """Check if LLM leaked any PII in its response using multiple detectors"""
        all_pii_issues = []

        # 1. Pattern-based PII detection (SSN, email, phone, etc.) - Fast and reliable
        pattern_pii_issues = self.pii_detector.detect(output)
        if pattern_pii_issues:
            logger.info(
                f"📋 Pattern-based detected {len(pattern_pii_issues)} PII instance(s)"
            )
            all_pii_issues.extend(pattern_pii_issues)

        # 2. NER-based PII detection (person names, organizations) - Context-aware
        if self.enable_ner_check and self.ner_detector:
            try:
                ner_pii_issues = self.ner_detector.detect_pii_entities(output)
                if ner_pii_issues:
                    logger.info(
                        f"🔍 NER detected {len(ner_pii_issues)} additional PII entity(ies)"
                    )
                    all_pii_issues.extend(ner_pii_issues)
            except Exception as e:
                logger.warning(f"NER PII detection failed: {e}")

        # 3. Presidio ML-based PII detection (comprehensive, ML-powered) - Most accurate
        if self.enable_presidio_check and self.presidio_detector:
            try:
                presidio_pii_issues = self.presidio_detector.detect(output)
                if presidio_pii_issues:
                    logger.info(
                        f"🤖 Presidio detected {len(presidio_pii_issues)} additional PII entity(ies)"
                    )
                    all_pii_issues.extend(presidio_pii_issues)
            except Exception as e:
                logger.warning(f"Presidio PII detection failed: {e}")

        # Remove duplicates (same PII detected by multiple detectors)
        unique_pii_issues = self._deduplicate_pii_issues(all_pii_issues)

        if unique_pii_issues:
            logger.warning(
                f"⚠️ LLM output contains {len(unique_pii_issues)} unique PII instance(s) - "
                "possible data leakage"
            )

        return unique_pii_issues

    def _deduplicate_pii_issues(
        self, issues: List[ValidationIssue]
    ) -> List[ValidationIssue]:
        """Remove duplicate PII detections from multiple detectors"""
        if not issues:
            return []

        # Group by position and text
        seen = set()
        unique_issues = []

        for issue in issues:
            # Create a key based on position and matched text
            key = (issue.position, issue.matched_text)
            if key not in seen:
                seen.add(key)
                unique_issues.append(issue)

        if len(issues) > len(unique_issues):
            logger.debug(
                f"Removed {len(issues) - len(unique_issues)} duplicate PII detections"
            )

        return unique_issues

    def _check_toxic_content(self, output: str) -> List[ValidationIssue]:
        """Check if LLM generated toxic content"""
        toxic_issues = self.toxic_detector.detect(output)

        if toxic_issues:
            logger.warning(
                f"LLM output contains {len(toxic_issues)} toxic content instance(s)"
            )

        return toxic_issues

    def _check_hallucinations(
        self, output: str, context: List[str]
    ) -> List[ValidationIssue]:
        """
        Check for potential hallucinations by looking for specific patterns

        Note: This is a basic implementation. For production, consider using
        specialized hallucination detection models or fact-checking APIs.
        """
        issues = []

        # Check for specific numbers/dates that weren't in context
        # This is a simplified check - real hallucination detection is more complex

        # Patterns that might indicate hallucination
        hallucination_patterns = [
            r"\b(definitely|certainly|absolutely|guaranteed)\b",  # Overconfident language
            r"\b(always|never|all|none|every)\b",  # Absolute statements
            r"\b(I am sure|I guarantee|I promise)\b",  # Inappropriate certainty
        ]

        import re

        for pattern in hallucination_patterns:
            matches = re.finditer(pattern, output, re.IGNORECASE)
            for match in matches:
                issue = ValidationIssue(
                    issue_type="HALLUCINATION_RISK",
                    severity=ValidationSeverity.MEDIUM,
                    description="Potentially overconfident or absolute statement",
                    matched_text=match.group(),
                    position=match.start(),
                )
                issues.append(issue)
                logger.debug(f"Potential hallucination risk: {match.group()}")

        return issues

    def _check_medical_disclaimer(
        self, output: str, query: str
    ) -> List[ValidationIssue]:
        """
        Check if medical advice needs a disclaimer
        """
        issues = []

        # Medical advice keywords
        medical_keywords = [
            "treatment",
            "medication",
            "diagnosis",
            "symptoms",
            "cure",
            "therapy",
            "prescription",
            "doctor",
            "medical",
        ]

        # Check if output contains medical advice
        output_lower = output.lower()
        has_medical_content = any(
            keyword in output_lower for keyword in medical_keywords
        )

        # Check if disclaimer already exists
        disclaimer_phrases = [
            "consult",
            "healthcare professional",
            "medical professional",
            "doctor",
            "physician",
            "not a substitute",
            "medical advice",
        ]

        has_disclaimer = any(phrase in output_lower for phrase in disclaimer_phrases)

        if has_medical_content and not has_disclaimer:
            issue = ValidationIssue(
                issue_type="MISSING_DISCLAIMER",
                severity=ValidationSeverity.HIGH,
                description="Medical advice without appropriate disclaimer",
                matched_text=None,
                position=None,
            )
            issues.append(issue)
            logger.warning("Medical content detected without disclaimer")

        return issues

    def _add_medical_disclaimer(self, output: str) -> str:
        """Add medical disclaimer to output"""
        disclaimer = (
            "\n\n⚕️ **Medical Disclaimer:** This information is for educational "
            "purposes only and should not be considered medical advice. "
            "Please consult with a qualified healthcare professional for "
            "medical diagnosis and treatment."
        )

        return output + disclaimer

    def _evaluate_output_safety(self, issues: List[ValidationIssue]) -> bool:
        """
        Evaluate if output is safe to show based on issues

        Args:
            issues: List of validation issues

        Returns:
            True if safe to show, False if should be blocked
        """
        if not issues:
            return True

        # Check for blocking conditions
        if self.block_on_pii:
            pii_issues = [i for i in issues if i.issue_type.startswith("PII_")]
            if pii_issues:
                logger.error(f"Output blocked: {len(pii_issues)} PII issue(s)")
                return False

        if self.block_on_toxic:
            toxic_issues = [i for i in issues if i.issue_type.startswith("TOXIC_")]
            if toxic_issues:
                logger.error(f"Output blocked: {len(toxic_issues)} toxic issue(s)")
                return False

        # CRITICAL severity always blocks
        critical_issues = [
            i for i in issues if i.severity == ValidationSeverity.CRITICAL
        ]
        if critical_issues:
            logger.error(f"Output blocked: {len(critical_issues)} CRITICAL issue(s)")
            return False

        return True

    def sanitize_output(self, output: str) -> str:
        """
        Sanitize output by removing PII and toxic content

        Args:
            output: LLM output to sanitize

        Returns:
            Sanitized output
        """
        sanitized = output

        # Redact PII
        if self.enable_pii_check:
            sanitized = self.pii_detector.redact_pii(sanitized)

        # Filter toxic content
        if self.enable_toxic_check:
            sanitized = self.toxic_detector.filter_toxic_content(sanitized)

        return sanitized

    def get_fallback_response(self, reason: str = "safety") -> str:
        """
        Get a safe fallback response when output is blocked

        Args:
            reason: Reason for blocking (safety, pii, toxic, etc.)

        Returns:
            Safe fallback message
        """
        fallback_messages = {
            "safety": (
                "I apologize, but I cannot provide that response due to safety concerns. "
                "Please rephrase your question or contact support for assistance."
            ),
            "pii": (
                "I apologize, but the response contained sensitive information that "
                "cannot be displayed. Please try rephrasing your question."
            ),
            "toxic": (
                "I apologize, but I cannot provide that response. "
                "Please rephrase your question in a different way."
            ),
            "hallucination": (
                "I apologize, but I'm not confident in the accuracy of my response. "
                "Please consult official medical resources or a healthcare professional."
            ),
        }

        return fallback_messages.get(reason, fallback_messages["safety"])


# Example usage
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    guardrails = OutputGuardrails(
        enable_pii_check=True,
        enable_toxic_check=True,
        enable_hallucination_check=True,
        require_medical_disclaimer=True,
        block_on_pii=True,
        block_on_toxic=True,
    )

    print("\n" + "=" * 80)
    print("OUTPUT GUARDRAILS TEST")
    print("=" * 80 + "\n")

    # Test cases
    test_cases = [
        {
            "name": "Clean medical response",
            "output": "Diabetes is managed through diet, exercise, and medication.",
            "query": "How to manage diabetes?",
            "context": ["Diabetes management includes diet and exercise"],
        },
        {
            "name": "Response with PII leakage",
            "output": "Patient John Doe (SSN: 123-45-6789) should take insulin.",
            "query": "What treatment is needed?",
            "context": [],
        },
        {
            "name": "Medical advice without disclaimer",
            "output": "You should take 500mg of metformin twice daily for your diabetes.",
            "query": "What medication should I take?",
            "context": ["Metformin is used for diabetes"],
        },
        {
            "name": "Overconfident response",
            "output": "This will definitely cure your diabetes in 30 days guaranteed!",
            "query": "Will this cure diabetes?",
            "context": ["Diabetes management strategies"],
        },
    ]

    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['name']}")
        print("-" * 80)
        print(f"Output: {test['output'][:60]}...")

        is_safe, issues, safe_output = guardrails.validate_output(
            test["output"], test["query"], test["context"]
        )

        if issues:
            print(f"\n❌ Issues found: {len(issues)}")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("\n✅ No issues found")

        print(f"\nSafe to show: {'YES ✓' if is_safe else 'NO ✗'}")

        if not is_safe:
            print(f"\nFallback: {guardrails.get_fallback_response('safety')}")
        elif safe_output != test["output"]:
            print(f"\nModified output: {safe_output[:100]}...")
