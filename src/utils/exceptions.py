"""
Custom exception classes for Medical Chatbot
"""


class MedicalChatbotError(Exception):
    """Base exception for Medical Chatbot"""

    pass


class ConfigurationError(MedicalChatbotError):
    """Raised when configuration is invalid or missing"""

    pass


class VectorStoreError(MedicalChatbotError):
    """Raised when vector store operations fail"""

    pass


class LLMError(MedicalChatbotError):
    """Raised when LLM operations fail"""

    pass


class IngestionError(MedicalChatbotError):
    """Raised when document ingestion fails"""

    pass


class ValidationError(MedicalChatbotError):
    """Raised when content validation fails"""

    pass


class PIIDetectionError(ValidationError):
    """Raised when PII detection fails"""

    pass


class ToxicContentError(ValidationError):
    """Raised when toxic content is detected"""

    pass


class MemoryError(MedicalChatbotError):
    """Raised when memory operations fail"""

    pass


class EvaluationError(MedicalChatbotError):
    """Raised when evaluation fails"""

    pass


# Example usage
if __name__ == "__main__":
    # Test exceptions
    try:
        raise ConfigurationError("Missing API key")
    except MedicalChatbotError as e:
        print(f"Caught exception: {e}")

    try:
        raise PIIDetectionError("PII detected in input")
    except ValidationError as e:
        print(f"Caught validation error: {e}")
