#!/usr/bin/env python3
"""Debug token to see what's wrong"""

import os
import sys
from pathlib import Path
import base64
import json

os.chdir(Path(__file__).parent)
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

from shared.graph_api import get_access_token

print("🔍 Debug Token Info\n")

token = get_access_token()
print(f"Token: {token[:30]}...{token[-20:]}\n")

# Decode JWT
parts = token.split('.')
if len(parts) != 3:
    print("❌ Not a valid JWT token")
    sys.exit(1)

# Decode payload
payload = parts[1]
payload += '=' * (4 - len(payload) % 4)
decoded = base64.urlsafe_b64decode(payload)
token_data = json.loads(decoded)

print("📋 Token Payload:")
print(json.dumps(token_data, indent=2))

print("\n" + "="*60)
print("🔑 Key Info:")
print("="*60)
print(f"Audience (aud): {token_data.get('aud')}")
print(f"Issuer (iss): {token_data.get('iss')}")
print(f"Scopes (scp): {token_data.get('scp')}")
print(f"App ID (appid): {token_data.get('appid')}")
print(f"Tenant ID (tid): {token_data.get('tid')}")
print(f"Account type: {token_data.get('idtyp', 'N/A')}")

# Check if organizational or personal
tid = token_data.get('tid', '')
if tid == '9188040d-6c67-4c5b-b112-36a304b66dad':
    print("\n⚠️  PERSONAL ACCOUNT (consumers)")
elif tid:
    print(f"\n⚠️  ORGANIZATIONAL ACCOUNT (tenant: {tid})")
else:
    print("\n⚠️  Unknown account type")

# Check scopes
scopes = token_data.get('scp', '')
print(f"\n📝 Scopes: {scopes}")

if 'Files.ReadWrite' in scopes:
    print("✅ Has Files.ReadWrite permission")
else:
    print("❌ Missing Files.ReadWrite permission")

if 'User.Read' in scopes:
    print("✅ Has User.Read permission")
else:
    print("⚠️  Missing User.Read permission (needed for /me endpoint)")
