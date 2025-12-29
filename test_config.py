"""Test script to debug configuration loading"""

import os

from app.core.config import Settings

print("=" * 80)
print("ENVIRONMENT VARIABLES FROM OS:")
print("=" * 80)
print(f"CORS_ORIGINS: {os.environ.get('CORS_ORIGINS', 'NOT SET')}")
print(f"CORS_ALLOW_METHODS: {os.environ.get('CORS_ALLOW_METHODS', 'NOT SET')}")
print(f"CORS_ALLOW_HEADERS: {os.environ.get('CORS_ALLOW_HEADERS', 'NOT SET')}")
print(f"AZURE_TRANSLATOR_KEY: {os.environ.get('AZURE_TRANSLATOR_KEY', 'NOT SET')[:20]}...")

print("\n" + "=" * 80)
print("TRYING TO LOAD SETTINGS:")
print("=" * 80)

try:
    settings = Settings()
    print("✅ Settings loaded successfully!")
    print(f"CORS_ORIGINS type: {type(settings.CORS_ORIGINS)}")
    print(f"CORS_ORIGINS value: {settings.CORS_ORIGINS}")
    print(f"AZURE_TRANSLATOR_KEY: {settings.AZURE_TRANSLATOR_KEY[:20]}...")
except Exception as e:
    print(f"❌ Error loading settings: {e}")
    print(f"Error type: {type(e)}")
    import traceback

    traceback.print_exc()
