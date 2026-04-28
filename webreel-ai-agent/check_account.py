"""
Check which OneDrive account is authenticated
"""
import sys
sys.path.insert(0, '/app/webreel-ai-agent')

from shared.graph_api import get_access_token
import requests
import json

print("Checking authenticated OneDrive account...\n")

try:
    token = get_access_token()
    headers = {'Authorization': f'Bearer {token}'}
    
    # Try different endpoints to get account info
    endpoints = [
        ('User Profile', 'https://graph.microsoft.com/v1.0/me'),
        ('Drive Info', 'https://graph.microsoft.com/v1.0/me/drive'),
        ('Drive Owner', 'https://graph.microsoft.com/v1.0/me/drive/owner'),
    ]
    
    for name, url in endpoints:
        print(f"Trying {name}...")
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                print(f"✓ Success!")
                print(json.dumps(data, indent=2))
                print()
            else:
                print(f"✗ Failed: {response.status_code}")
                print(f"  {response.text[:200]}")
                print()
        except Exception as e:
            print(f"✗ Error: {e}\n")
    
    # Check token cache file for account info
    print("\nChecking token cache...")
    try:
        import msal
        cache = msal.SerializableTokenCache()
        cache_file = "/app/webreel-ai-agent/shared/token_cache.bin"
        
        with open(cache_file, 'r') as f:
            cache_data = f.read()
            cache.deserialize(cache_data)
            
        # Parse cache to find account info
        import json
        cache_dict = json.loads(cache_data)
        
        if 'Account' in cache_dict:
            print("Accounts in cache:")
            for account_key, account_data in cache_dict['Account'].items():
                print(f"\n  Account: {account_key}")
                print(f"  Username: {account_data.get('username')}")
                print(f"  Name: {account_data.get('name')}")
                print(f"  Environment: {account_data.get('environment')}")
                print(f"  Home Account ID: {account_data.get('home_account_id')}")
    except Exception as e:
        print(f"✗ Cache error: {e}")
        
except Exception as e:
    print(f"✗ Token error: {e}")
