import pytest
from src.utils.exceptions import (
    MedicalChatbotError,
    ConfigurationError,
    VectorStoreError,
    LLMError,
    IngestionError,
    ValidationError,
    PIIDetectionError,
    ToxicContentError
)

class TestExceptions:
    def test_base_exception(self):
        """Test base exception"""
        err = MedicalChatbotError("Something went wrong")
        assert isinstance(err, Exception)
        assert str(err) == "Something went wrong"

    def test_configuration_error(self):
        """Test configuration specific error"""
        err = ConfigurationError("Missing key")
        assert isinstance(err, MedicalChatbotError)
        assert str(err) == "Missing key"

    def test_ingestion_error(self):
        err = IngestionError("File not found")
        assert isinstance(err, MedicalChatbotError)

    def test_vector_store_error(self):
        err = VectorStoreError("DB connection failed")
        assert isinstance(err, MedicalChatbotError)

    def test_llm_error(self):
        err = LLMError("API timeout")
        assert isinstance(err, MedicalChatbotError)

    def test_validation_error(self):
        err = ValidationError("Validation failed")
        assert isinstance(err, MedicalChatbotError)

    def test_pii_error(self):
        err = PIIDetectionError("PII detected")
        assert isinstance(err, ValidationError)

    def test_toxic_error(self):
        err = ToxicContentError("Toxic content")
        assert isinstance(err, ValidationError)

