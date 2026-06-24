"""
Generate secure INTERNAL_API_KEY for OS Worker authentication.

Usage:
    python generate_api_key.py
"""

import secrets

if __name__ == "__main__":
    api_key = secrets.token_urlsafe(32)
    
    print("=" * 60)
    print("Generated INTERNAL_API_KEY")
    print("=" * 60)
    print()
    print(f"INTERNAL_API_KEY={api_key}")
    print()
    print("Add this to your .env file:")
    print("  1. VPS (Linux): webreel-ai-agent/.env")
    print("  2. OS Worker (Windows): Same key in worker .env")
    print()
    print("⚠️  Keep this key secret! Do not commit to git.")
    print("=" * 60)
