"""
Demo Script for Content Analyzer Module
Demonstrates PII detection and toxic content validation

Run from Content_Analyzer directory:
    python demo.py
"""

# Since we're running from Content_Analyzer folder, we can import directly
from config import ValidationConfig
from validator import ContentValidator
from utils import (
    format_validation_report,
    calculate_risk_score,
    create_validation_metrics,
)


def print_header(title: str):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def print_result(is_safe: bool, issues: list):
    """Print validation result"""
    if is_safe:
        print("✅ SAFE - Content can be processed")
    else:
        print("❌ BLOCKED - Content contains sensitive information")

    if issues:
        print(f"\nFound {len(issues)} issue(s):")
        for issue in issues:
            print(f"  • {issue}")


def demo_basic_validation():
    """Demo 1: Basic validation"""
    print_header("DEMO 1: Basic Content Validation")

    validator = ContentValidator()

    test_cases = [
        (
            "Clean medical text",
            "Diabetes is a chronic disease that affects blood sugar levels.",
        ),
        ("Contains email", "Contact us at support@medical.com for assistance."),
        ("Contains SSN", "Patient SSN: 123-45-6789 has type 2 diabetes."),
        ("Contains profanity", "This damn system doesn't work properly!"),
        ("Multiple issues", "Email john@test.com, SSN: 987-65-4321, this is shit!"),
    ]

    for name, text in test_cases:
        print(f"Test: {name}")
        print(f"Text: {text}")
        print("-" * 80)

        is_safe, issues = validator.validate(text)
        print_result(is_safe, issues)
        print()


def demo_custom_config():
    """Demo 2: Custom configuration"""
    print_header("DEMO 2: Custom Configuration")

    # Strict configuration - block everything
    strict_config = ValidationConfig(
        enable_pii_detection=True,
        enable_toxic_detection=True,
        pii_block_on_critical=True,
        pii_block_on_high=True,  # Block emails and phones too
        toxic_block_on_critical=True,
        toxic_block_on_high=True,  # Block profanity too
        log_issues=True,
        verbose=False,
    )

    strict_validator = ContentValidator(strict_config)

    text = "Contact me at john@email.com or call 555-1234"

    print("Configuration: STRICT (block on HIGH and CRITICAL)")
    print(f"Text: {text}")
    print("-" * 80)

    is_safe, issues = strict_validator.validate(text)
    print_result(is_safe, issues)

    # Lenient configuration - warnings only
    lenient_config = ValidationConfig(
        enable_pii_detection=True,
        enable_toxic_detection=True,
        pii_block_on_critical=True,
        pii_block_on_high=False,  # Allow emails and phones
        toxic_block_on_critical=False,
        toxic_block_on_high=False,  # Allow all toxic content
        log_issues=True,
        verbose=False,
    )

    lenient_validator = ContentValidator(lenient_config)

    print("\n\nConfiguration: LENIENT (block only CRITICAL PII)")
    print(f"Text: {text}")
    print("-" * 80)

    is_safe, issues = lenient_validator.validate(text)
    print_result(is_safe, issues)


def demo_rag_pipeline():
    """Demo 3: RAG pipeline integration"""
    print_header("DEMO 3: RAG Pipeline Integration")

    validator = ContentValidator()

    # Simulate user query
    user_query = "What are the symptoms of diabetes?"

    print("Step 1: Validate User Query")
    print(f"Query: {user_query}")
    print("-" * 80)

    is_safe, issues = validator.validate(user_query)
    print_result(is_safe, issues)

    if not is_safe:
        print("\n❌ Query blocked - cannot proceed")
        return

    # Simulate retrieved documents
    print("\n\nStep 2: Validate Retrieved Context")
    print("-" * 80)

    documents = [
        "Diabetes is a chronic disease that affects how your body processes blood sugar.",
        "Patient John Doe, SSN: 123-45-6789, diagnosed with type 2 diabetes in 2020.",
        "Common symptoms include increased thirst, frequent urination, and fatigue.",
        "For more info, email us at info@hospital.com or call 555-HELP (555-4357).",
        "Treatment may include medication, diet changes, and regular exercise.",
    ]

    safe_docs = []
    blocked_docs = []

    for i, doc in enumerate(documents, 1):
        print(f"\nDocument {i}: {doc[:60]}...")
        is_safe, issues = validator.validate(doc)

        if is_safe:
            safe_docs.append(doc)
            print("  ✅ Safe")
        else:
            blocked_docs.append((doc, issues))
            print(f"  ❌ Blocked ({len(issues)} issue(s))")

    print("\n" + "=" * 80)
    print(f"Results: {len(safe_docs)}/{len(documents)} documents safe to send to LLM")
    print(f"Blocked: {len(blocked_docs)} documents")
    print("=" * 80)

    if safe_docs:
        print("\n✅ Safe documents to send to LLM:")
        for i, doc in enumerate(safe_docs, 1):
            print(f"  {i}. {doc[:70]}...")


def demo_content_sanitization():
    """Demo 4: Content sanitization"""
    print_header("DEMO 4: Content Sanitization")

    validator = ContentValidator()

    text = """
    Patient Information:
    Name: John Doe
    Email: john.doe@email.com
    Phone: 555-123-4567
    SSN: 123-45-6789
    Job: Software Engineer
    Medical Record: MRN A987654
    
    This damn system is so slow! I hate waiting.
    """

    print("Original Text:")
    print("-" * 80)
    print(text)

    print("\n\nSanitized Text (PII redacted, toxic content filtered):")
    print("-" * 80)
    sanitized = validator.sanitize_content(text, redact_pii=True, filter_toxic=True)
    print(sanitized)


def demo_validation_metrics():
    """Demo 5: Validation metrics and reporting"""
    print_header("DEMO 5: Validation Metrics & Risk Scoring")

    validator = ContentValidator()

    text = """
    Contact: john@email.com, Phone: 555-1234
    SSN: 123-45-6789, Credit Card: 1234-5678-9012-3456
    This is a damn mess! I hate this stupid system!
    """

    print("Text to analyze:")
    print("-" * 80)
    print(text)

    is_safe, issues = validator.validate(text)

    print("\n\nValidation Report:")
    print("-" * 80)
    print(format_validation_report(issues, include_details=True))

    print("\n\nValidation Metrics:")
    print("-" * 80)
    metrics = create_validation_metrics(issues)
    print(f"Total Issues: {metrics['total_issues']}")
    print(f"Has PII: {metrics['has_pii']}")
    print(f"Has Toxic Content: {metrics['has_toxic_content']}")
    print(f"Is Safe: {metrics['is_safe']}")
    print("\nSeverity Breakdown:")
    for severity, count in metrics["severity_breakdown"].items():
        if count > 0:
            print(f"  • {severity.upper()}: {count}")

    risk_score = calculate_risk_score(issues)
    print(f"\n🎯 Risk Score: {risk_score:.1f}/10.0")

    if risk_score >= 7.0:
        print("   ⚠️  HIGH RISK - Immediate action required")
    elif risk_score >= 4.0:
        print("   ⚠️  MEDIUM RISK - Review recommended")
    else:
        print("   ✅ LOW RISK - Acceptable")


def main():
    """Run all demos"""
    print("\n" + "=" * 80)
    print("  CONTENT ANALYZER - DEMONSTRATION")
    print("  PII Detection & Toxic Content Validation")
    print("=" * 80)

    try:
        demo_basic_validation()
        input("\nPress Enter to continue to Demo 2...")

        demo_custom_config()
        input("\nPress Enter to continue to Demo 3...")

        demo_rag_pipeline()
        input("\nPress Enter to continue to Demo 4...")

        demo_content_sanitization()
        input("\nPress Enter to continue to Demo 5...")

        demo_validation_metrics()

        print("\n" + "=" * 80)
        print("  ✅ ALL DEMOS COMPLETED SUCCESSFULLY")
        print("=" * 80 + "\n")

    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
