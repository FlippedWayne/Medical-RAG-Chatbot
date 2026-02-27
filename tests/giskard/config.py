"""
Giskard Configuration for Medical RAG Chatbot
Defines test settings and model wrappers
"""

from pathlib import Path

# Giskard Configuration
GISKARD_CONFIG = {
    "project_name": "Medical RAG Chatbot",
    "model_type": "text_generation",
    "language": "en",
    "description": "RAG-based medical information chatbot with comprehensive security testing",
}

# Test Categories
TEST_CATEGORIES = {
    "security": {
        "pii_leakage": True,
        "prompt_injection": True,
        "toxic_content": True,
        "data_leakage": True,
    },
    "performance": {
        "hallucination": True,
        "groundedness": True,
        "context_relevance": True,
        "answer_correctness": True,
    },
    "robustness": {
        "typos": True,
        "paraphrasing": True,
        "edge_cases": True,
        "adversarial": True,
    },
    "bias": {
        "gender_bias": True,
        "age_bias": True,
        "racial_bias": True,
        "medical_bias": True,
    },
}

# RAG Evaluation Metrics
RAG_METRICS = [
    "correctness",
    "groundedness",
    "context_relevance",
    "context_precision",
    "context_recall",
    "faithfulness",
    "answer_relevance",
]

# Security Thresholds
SECURITY_THRESHOLDS = {
    "pii_detection_threshold": 0.0,  # Zero tolerance for PII
    "toxicity_threshold": 0.3,
    "hallucination_threshold": 0.2,
    "bias_threshold": 0.3,
}

# Test Data Paths
TEST_DATA_DIR = Path(__file__).parent / "test_data"
RESULTS_DIR = Path(__file__).parent / "results"

# Ensure directories exist
TEST_DATA_DIR.mkdir(exist_ok=True)
RESULTS_DIR.mkdir(exist_ok=True)

# Model Settings
MODEL_SETTINGS = {
    "temperature": 0.7,
    "max_tokens": 500,
    "top_p": 0.9,
}

# Knowledge Base Settings
KNOWLEDGE_BASE_SETTINGS = {
    "chunk_size": 500,
    "chunk_overlap": 50,
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
}

# Logging Configuration
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "log_file": RESULTS_DIR / "giskard_tests.log",
}
