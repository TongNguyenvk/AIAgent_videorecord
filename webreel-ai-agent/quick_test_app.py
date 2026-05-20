#!/usr/bin/env python3
"""
Quick test - Chỉ cần chạy để xem app có OK không.
Không upload file, chỉ check token và permissions.

Usage:
    python quick_test_app.py
"""

import os
import sys
from pathlib import Path

# Set working directory to script location
os.chdir(Path(__file__).parent)
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
# Load .env from current directory
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path, override=True)

def main():
    print("🔍 Quick Test - Graph API App\n")
    
    # 1. Check Client ID
    client_id = os.getenv("MS_CLIENT_ID", "")
    if not client_id:
        print("❌ MS_CLIENT_ID không có trong .env")
        print("   Thêm dòng: MS_CLIENT_ID=<your_client_id>")
        return False
    
    print(f"✅ Client ID: {client_id[:8]}...{client_id[-4:]}\n")
    
    # 2. Try get token
    try:
        from shared.graph_api import get_access_token
        import requests
        
        print("🔑 Đang lấy token...")
        print("   (Nếu lần đầu, bạn sẽ thấy Device Code để login)\n")
        
        token = get_access_token()
        print("✅ Token OK!\n")
        
        # 3. Test API call
        print("🌐 Testing Graph API...")
        headers = {'Authorization': f'Bearer {token}'}
        
        # Get user info
        r = requests.get('https://graph.microsoft.com/v1.0/me', headers=headers)
        if r.status_code == 200:
            user = r.json()
            print(f"✅ User: {user.get('displayName', 'N/A')}")
        else:
            print(f"❌ API failed: {r.status_code}")
            print(f"   Response: {r.text}")
            return False
        
        # Check OneDrive access
        r = requests.get('https://graph.microsoft.com/v1.0/me/drive', headers=headers)
        if r.status_code == 200:
            print("✅ OneDrive access OK")
        else:
            print(f"❌ OneDrive access failed: {r.status_code}")
            return False
        
        print("\n" + "="*50)
        print("🎉 APP ĐÃ SẴN SÀNG SỬ DỤNG!")
        print("="*50)
        print("\nBạn có thể:")
        print("1. Dùng app này cho WebReel (không cần tạo app mới)")
        print("2. Token sẽ tự động refresh")
        print("3. Không cần login lại (trừ khi xóa token_cache.bin)")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
