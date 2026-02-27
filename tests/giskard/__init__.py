"""
Giskard Testing Suite for Medical RAG Chatbot
"""

__version__ = "1.0.0"

from .config import (
    GISKARD_CONFIG,
    TEST_CATEGORIES,
    RAG_METRICS,
    SECURITY_THRESHOLDS,
)

try:
    from .model_wrapper import (
        MedicalRAGModel,
        create_giskard_model,
        create_test_dataset,
    )
    from .security_tests import GiskardSecurityTester
    from .rag_evaluation import RAGEvaluator

    __all__ = [
        "GISKARD_CONFIG",
        "TEST_CATEGORIES",
        "RAG_METRICS",
        "SECURITY_THRESHOLDS",
        "MedicalRAGModel",
        "create_giskard_model",
        "create_test_dataset",
        "GiskardSecurityTester",
        "RAGEvaluator",
    ]
except ImportError as e:
    print(f"⚠️ Some imports failed: {e}")
    print("⚠️ Make sure all dependencies are installed")

    __all__ = [
        "GISKARD_CONFIG",
        "TEST_CATEGORIES",
        "RAG_METRICS",
        "SECURITY_THRESHOLDS",
    ]
