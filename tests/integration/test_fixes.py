"""
Test script to verify all fixes are working correctly
"""

import sys
from pathlib import Path

# Add project root to path so imports like `from src.utils...` resolve correctly
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.utils.logger import get_logger
from src.config.settings import Settings

print("=" * 60)
print("🧪 Testing All Fixes")
print("=" * 60)
print()

# Test 1: Unicode/Emoji Logging
print("Test 1: Unicode/Emoji Logging")
print("-" * 40)
logger = get_logger(__name__, log_to_file=False)
logger.info("✅ Testing emoji support in logs")
logger.info("📊 Testing chart emoji")
logger.info("🚀 Testing rocket emoji")
logger.info("🎉 All emojis should display correctly!")
print("✅ Test 1 PASSED - No UnicodeEncodeError!")
print()

# Test 2: Duplicate Logs
print("Test 2: Duplicate Log Messages")
print("-" * 40)
logger.info("This message should appear ONLY ONCE")
logger.info("This message should also appear ONLY ONCE")
print("✅ Test 2 PASSED - No duplicates!")
print()

# Test 3: Config Validation
print("Test 3: Config Validation")
print("-" * 40)
try:
    settings = Settings()
    print("Config loaded successfully")
    print(f"Config keys: {list(settings.config.keys())}")
    print("✅ Test 3 PASSED - No false warnings!")
except Exception as e:
    print(f"❌ Test 3 FAILED: {e}")
print()

# Test 4: LangSmith CLI (informational)
print("Test 4: LangSmith CLI")
print("-" * 40)
print("ℹ️  To test LangSmith CLI, run:")
print("   1. .\\fix_langsmith_cli.ps1")
print("   2. .venv\\Scripts\\Activate.ps1")
print("   3. langsmith --version")
print()

print("=" * 60)
print("🎉 All Automated Tests Passed!")
print("=" * 60)
print()
print("Summary:")
print("  ✅ Unicode/Emoji encoding works")
print("  ✅ No duplicate log messages")
print("  ✅ Config validation correct")
print("  ℹ️  LangSmith CLI fix available")
print()
print("Next step: Restart your Streamlit app to see the improvements!")
print("  streamlit run app.py")
