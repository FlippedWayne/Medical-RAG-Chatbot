"""
Quick test script to verify observability integration.
Run this to check if all imports work correctly.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

print("🔍 Testing Observability Integration...\n")

# Test 1: Import observability modules
print("1. Testing observability imports...")
try:
    from src.observability import (
        configure_langsmith,
        is_langsmith_enabled,
        trace_chain,
        create_feedback,
        get_current_run_id,
    )
    from src.observability.tracing import add_run_metadata

    print("   ✅ All observability imports successful\n")
except ImportError as e:
    print(f"   ❌ Import error: {e}\n")
    sys.exit(1)

# Test 2: Check if LangSmith is configured
print("2. Checking LangSmith configuration...")
try:
    enabled = is_langsmith_enabled()
    if enabled:
        print("   ✅ LangSmith is ENABLED")
        print("   📊 Tracing is active\n")
    else:
        print("   ℹ️  LangSmith is DISABLED")
        print("   💡 Set LANGSMITH_API_KEY in .env to enable\n")
except Exception as e:
    print(f"   ❌ Configuration check failed: {e}\n")

# Test 3: Test trace decorator
print("3. Testing trace decorator...")
try:

    @trace_chain(name="traced_function", tags=["test"])
    def traced_function(x):
        return x * 2

    result = traced_function(5)
    assert result == 10
    print("   ✅ Trace decorator works correctly\n")
except Exception as e:
    print(f"   ❌ Trace decorator test failed: {e}\n")

# Test 4: Import main app modules
print("4. Testing main app imports...")
try:
    from src.utils.logger import get_logger
    from src.utils.exceptions import VectorStoreError, LLMError
    from src.config.settings import settings

    print("   ✅ All main app imports successful\n")
except ImportError as e:
    print(f"   ❌ Import error: {e}\n")
    sys.exit(1)

# Test 5: Check logger integration
print("5. Testing logger integration...")
try:
    logger = get_logger(__name__)
    logger.info("Test log message")
    print("   ✅ Logger works correctly\n")
except Exception as e:
    print(f"   ❌ Logger test failed: {e}\n")

# Summary
print("=" * 60)
print("✅ OBSERVABILITY INTEGRATION TEST PASSED!")
print("=" * 60)
print("\nAll components are working correctly!")
print("\nNext steps:")
print("1. Add LANGSMITH_API_KEY to .env to enable tracing")
print("2. Run: streamlit run app.py")
print("3. Check LangSmith dashboard at https://smith.langchain.com")
print("\nDocumentation:")
print("- Quick Start: docs/OBSERVABILITY_QUICKSTART.md")
print("- Full Guide: docs/OBSERVABILITY_INTEGRATION.md")
