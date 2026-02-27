"""
Content Analyzer Package
Provides content validation, PII detection, and toxic content detection
"""

from .validator import ContentValidator
from .config import (
    ValidationConfig,
    ValidationIssue,
    ValidationSeverity,
    PIIDetectionMode,
    ToxicDetectionMode,
)
from .pii_detector import PIIDetector
from .toxic_detector import ToxicContentDetector

# Optional ML-based detectors (may not be available)
try:
    from .pii_detector_presidio import PIIDetectorPresidio

    PRESIDIO_AVAILABLE = True
except ImportError:
    PRESIDIO_AVAILABLE = False

try:
    from .toxic_detector_ml import ToxicContentDetectorML

    DETOXIFY_AVAILABLE = True
except ImportError:
    DETOXIFY_AVAILABLE = False

try:
    from .ner_detector import NERDetector

    NER_AVAILABLE = True
except ImportError:
    NER_AVAILABLE = False

__all__ = [
    # Main validator
    "ContentValidator",
    # Configuration
    "ValidationConfig",
    "ValidationIssue",
    "ValidationSeverity",
    "PIIDetectionMode",
    "ToxicDetectionMode",
    # Detectors
    "PIIDetector",
    "ToxicContentDetector",
    # Availability flags
    "PRESIDIO_AVAILABLE",
    "DETOXIFY_AVAILABLE",
    "NER_AVAILABLE",
]

# Add optional detectors to __all__ if available
if PRESIDIO_AVAILABLE:
    __all__.append("PIIDetectorPresidio")

if DETOXIFY_AVAILABLE:
    __all__.append("ToxicContentDetectorML")

if NER_AVAILABLE:
    __all__.append("NERDetector")

__version__ = "0.1.0"
