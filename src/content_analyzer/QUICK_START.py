"""
Quick Start Guide - Content Analyzer
Simple examples to get started quickly
"""

# ============================================================================
# EXAMPLE 1: Basic Validation
# ============================================================================

from Content_Analyzer import ContentValidator

# Initialize validator
validator = ContentValidator()

# Validate text
text = "Contact me at john@email.com"
is_safe, issues = validator.validate(text)

print(f"Safe: {is_safe}")
print(f"Issues: {len(issues)}")


# ============================================================================
# EXAMPLE 2: Validate User Query in RAG
# ============================================================================


def validate_user_query(query: str) -> bool:
    """Validate user query before processing"""
    validator = ContentValidator()
    is_safe, issues = validator.validate(query)

    if not is_safe:
        print(f"❌ Query blocked: {len(issues)} issue(s) found")
        for issue in issues:
            print(f"  - {issue}")
        return False

    return True


# Usage
user_query = "What are the symptoms of diabetes?"
if validate_user_query(user_query):
    print("✅ Query is safe - proceed with RAG pipeline")


# ============================================================================
# EXAMPLE 3: Validate Retrieved Documents
# ============================================================================


def filter_safe_documents(documents: list) -> list:
    """Filter out documents with PII or toxic content"""
    validator = ContentValidator()
    safe_docs = []

    for doc in documents:
        # Assuming doc has .page_content attribute (LangChain Document)
        content = doc.page_content if hasattr(doc, "page_content") else str(doc)

        is_safe, issues = validator.validate(content)
        if is_safe:
            safe_docs.append(doc)
        else:
            print(f"⚠️  Blocked document with {len(issues)} issue(s)")

    return safe_docs


# Usage
# retrieved_docs = vectorstore.similarity_search(query, k=5)
# safe_docs = filter_safe_documents(retrieved_docs)
# # Send safe_docs to LLM


# ============================================================================
# EXAMPLE 4: Sanitize Content (Redact PII)
# ============================================================================


def sanitize_medical_record(text: str) -> str:
    """Sanitize medical record by redacting PII"""
    validator = ContentValidator()

    # Redact PII and filter toxic content
    sanitized = validator.sanitize_content(text, redact_pii=True, filter_toxic=True)

    return sanitized


# Usage
medical_text = """
Patient: John Doe
Email: john.doe@hospital.com
SSN: 123-45-6789
Diagnosis: Type 2 Diabetes
"""

sanitized = sanitize_medical_record(medical_text)
print("Sanitized:")
print(sanitized)


# ============================================================================
# EXAMPLE 5: Custom Configuration
# ============================================================================

from Content_Analyzer import ValidationConfig

# Create strict configuration
strict_config = ValidationConfig(
    enable_pii_detection=True,
    enable_toxic_detection=True,
    pii_block_on_critical=True,
    pii_block_on_high=True,  # Block emails and phones too
    toxic_block_on_critical=True,
    toxic_block_on_high=True,  # Block all toxic content
    log_issues=True,
    verbose=True,
)

strict_validator = ContentValidator(strict_config)

# Now emails and phones will be blocked
text = "Contact: john@email.com"
is_safe, issues = strict_validator.validate(text)
print(f"Strict mode - Safe: {is_safe}")  # Will be False


# ============================================================================
# EXAMPLE 6: Get Validation Summary
# ============================================================================


def analyze_content(text: str):
    """Analyze content and get detailed summary"""
    validator = ContentValidator()
    is_safe, issues = validator.validate(text)

    if issues:
        summary = validator.get_validation_summary(issues)

        print(f"Total Issues: {summary['total_issues']}")
        print(f"PII Issues: {summary['pii_count']}")
        print(f"Toxic Issues: {summary['toxic_count']}")
        print("\nBy Severity:")
        for severity, count in summary["by_severity"].items():
            if count > 0:
                print(f"  {severity}: {count}")

    return is_safe


# Usage
text = "Email: test@test.com, SSN: 123-45-6789, damn this is bad"
analyze_content(text)


# ============================================================================
# EXAMPLE 7: Integration with Streamlit (main.py)
# ============================================================================

"""
# Add to your main.py Streamlit app:

import streamlit as st
from Content_Analyzer import ContentValidator

# Initialize validator (do this once)
if 'validator' not in st.session_state:
    st.session_state.validator = ContentValidator()

# In your query processing function:
def process_user_query(query: str):
    validator = st.session_state.validator
    
    # Validate query
    is_safe, issues = validator.validate(query)
    
    if not is_safe:
        st.error("⚠️ Your query contains sensitive information and cannot be processed")
        with st.expander("See details"):
            for issue in issues:
                st.write(f"- {issue}")
        return None
    
    # Proceed with RAG pipeline
    # ... retrieve documents ...
    # ... validate documents ...
    # ... send to LLM ...
"""


# ============================================================================
# EXAMPLE 8: Batch Processing
# ============================================================================


def validate_multiple_texts(texts: list) -> dict:
    """Validate multiple texts and return summary"""
    validator = ContentValidator()

    results = validator.validate_batch(texts)

    summary = {
        "total": len(texts),
        "safe": sum(1 for is_safe, _ in results if is_safe),
        "blocked": sum(1 for is_safe, _ in results if not is_safe),
        "total_issues": sum(len(issues) for _, issues in results),
    }

    return summary


# Usage
texts = ["Clean medical text", "Contains email@test.com", "Has SSN: 123-45-6789"]

summary = validate_multiple_texts(texts)
print(f"Validated {summary['total']} texts")
print(f"Safe: {summary['safe']}, Blocked: {summary['blocked']}")


# ============================================================================
# EXAMPLE 9: Check for Specific PII Type
# ============================================================================

from Content_Analyzer import PIIDetector

detector = PIIDetector()

text = "Contact: john@email.com, Phone: 555-1234"

# Check for specific PII type
email_issues = detector.detect_by_type(text, "email")
phone_issues = detector.detect_by_type(text, "phone")

print(f"Found {len(email_issues)} email(s)")
print(f"Found {len(phone_issues)} phone number(s)")


# ============================================================================
# EXAMPLE 10: Calculate Risk Score
# ============================================================================

from Content_Analyzer import ContentValidator
from Content_Analyzer.utils import calculate_risk_score

validator = ContentValidator()

text = "SSN: 123-45-6789, Credit Card: 1234-5678-9012-3456"
is_safe, issues = validator.validate(text)

risk_score = calculate_risk_score(issues)
print(f"Risk Score: {risk_score:.1f}/10.0")

if risk_score >= 7.0:
    print("⚠️  HIGH RISK")
elif risk_score >= 4.0:
    print("⚠️  MEDIUM RISK")
else:
    print("✅ LOW RISK")


# ============================================================================
# TIPS & BEST PRACTICES
# ============================================================================

"""
1. Initialize validator once and reuse it (especially in Streamlit)
2. Use strict config for sensitive applications (medical, financial)
3. Always validate user input before processing
4. Validate retrieved context before sending to LLM
5. Log all validation issues for audit trail
6. Sanitize content when displaying to users
7. Use batch processing for multiple documents
8. Monitor risk scores for compliance reporting
9. Update PII patterns regularly for your domain
10. Test with real-world examples from your use case
"""
