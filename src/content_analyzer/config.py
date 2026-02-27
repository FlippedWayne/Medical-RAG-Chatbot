"""
Configuration for Content Analyzer
Defines severity levels, detection rules, and validation settings
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional


class ValidationSeverity(Enum):
    """Severity levels for validation issues"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PIIDetectionMode(Enum):
    """PII detection modes"""

    REGEX = "regex"  # Fast, regex-based detection (default)
    PRESIDIO = "presidio"  # ML-based, context-aware detection (more accurate)
    HYBRID = "hybrid"  # Use both methods


class ToxicDetectionMode(Enum):
    """Toxic content detection modes"""

    WORDLIST = "wordlist"  # Fast, word-list based detection (default)
    ML = "ml"  # ML-based, context-aware detection (Detoxify)
    HYBRID = "hybrid"  # Use both methods


@dataclass
class ValidationIssue:
    """Represents a validation issue found in content"""

    issue_type: str
    severity: ValidationSeverity
    description: str
    matched_text: Optional[str] = None
    position: Optional[int] = None
    metadata: Optional[Dict] = None  # Additional metadata (e.g., confidence scores)

    def __str__(self):
        return f"[{self.severity.value.upper()}] {self.issue_type}: {self.description}"


@dataclass
class ValidationConfig:
    """Configuration for content validation"""

    # PII Detection Settings
    enable_pii_detection: bool = True
    pii_detection_mode: PIIDetectionMode = (
        PIIDetectionMode.REGEX
    )  # REGEX, PRESIDIO, or HYBRID
    pii_block_on_critical: bool = True
    pii_block_on_high: bool = False

    # Presidio-specific settings
    presidio_score_threshold: float = 0.5  # Minimum confidence score (0.0-1.0)
    presidio_language: str = "en"  # Language code

    # Toxic Content Settings
    enable_toxic_detection: bool = True
    toxic_detection_mode: ToxicDetectionMode = (
        ToxicDetectionMode.WORDLIST
    )  # WORDLIST, ML, or HYBRID
    toxic_block_on_critical: bool = True
    toxic_block_on_high: bool = False

    # Detoxify-specific settings
    detoxify_model_type: str = "original"  # 'original', 'unbiased', or 'multilingual'
    detoxify_threshold: float = 0.5  # Minimum confidence score (0.0-1.0)

    # Logging Settings
    log_issues: bool = True
    verbose: bool = False

    # Custom PII Patterns (can be extended)
    custom_pii_patterns: Optional[Dict[str, str]] = None

    # Custom Toxic Words (can be extended)
    custom_toxic_words: Optional[List[str]] = None


# Default PII Detection Patterns
PII_PATTERNS = {
    "email": {
        "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "severity": ValidationSeverity.HIGH,
        "description": "Email address detected",
    },
    "phone": {
        "pattern": r"(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
        "severity": ValidationSeverity.HIGH,
        "description": "Phone number detected",
    },
    "ssn": {
        "pattern": r"\b\d{3}-\d{2}-\d{4}\b",
        "severity": ValidationSeverity.CRITICAL,
        "description": "Social Security Number detected",
    },
    "credit_card": {
        "pattern": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
        "severity": ValidationSeverity.CRITICAL,
        "description": "Potential credit card number detected",
    },
    "ip_address": {
        "pattern": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "severity": ValidationSeverity.MEDIUM,
        "description": "IP address detected",
    },
    "medical_record": {
        "pattern": r"\b(MRN|MR#|Medical Record|Patient ID)[\s:]*[A-Z0-9]{6,12}\b",
        "severity": ValidationSeverity.CRITICAL,
        "description": "Medical record number detected",
    },
    "dob": {
        "pattern": r"\b(DOB|Date of Birth|Born)[\s:]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        "severity": ValidationSeverity.HIGH,
        "description": "Date of birth detected",
    },
    "passport": {
        "pattern": r"\b[A-Z]{1,2}\d{6,9}\b",
        "severity": ValidationSeverity.CRITICAL,
        "description": "Potential passport number detected",
    },
    "drivers_license": {
        "pattern": r"\b(DL|Driver\'s License|License #)[\s:]*[A-Z0-9]{6,12}\b",
        "severity": ValidationSeverity.HIGH,
        "description": "Driver's license detected",
    },
    "bank_account": {
        "pattern": r"\b(Account|Acct)[\s#:]*\d{8,17}\b",
        "severity": ValidationSeverity.CRITICAL,
        "description": "Bank account number detected",
    },
}


# Toxic Content Categories
TOXIC_CATEGORIES = {
    "profanity": {
        "words": ["fuck", "shit", "damn", "bitch", "ass", "bastard", "crap", "hell"],
        "severity": ValidationSeverity.MEDIUM,
        "description": "Profanity detected",
    },
    "hate_speech": {
        "words": ["hate", "kill", "murder", "terrorist", "nazi", "racist"],
        "severity": ValidationSeverity.HIGH,
        "description": "Potential hate speech detected",
    },
    "sexual_content": {
        "words": ["porn", "xxx", "sex", "nude", "naked", "explicit"],
        "severity": ValidationSeverity.HIGH,
        "description": "Sexual content detected",
    },
    "violence": {
        "words": ["bomb", "weapon", "gun", "knife", "attack", "assault", "shoot"],
        "severity": ValidationSeverity.HIGH,
        "description": "Violent content detected",
    },
    "harassment": {
        "words": ["stupid", "idiot", "moron", "dumb", "loser", "ugly"],
        "severity": ValidationSeverity.MEDIUM,
        "description": "Potentially harassing content detected",
    },
}
