"""
Vi du su dung Google Drive API thay vi browser automation.
Cach nay KHONG BI BOT DETECTION.

Cai dat:
    pip install google-auth google-auth-oauthlib google-api-python-client

Setup:
    1. Tao project tren Google Cloud Console
    2. Bat Google Drive API
    3. Tao OAuth 2.0 credentials (Desktop app)
    4. Tai credentials.json ve thu muc nay

Cach dung:
    python google_drive_api_example.py
"""

import os
import pickle
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build


SCOPES = ['https://www.googleapis.com/auth/drive']
TOKEN_FILE = Path(__file__).parent / "output" / "google_token.pickle"
CREDENTIALS_FILE = Path(__file__).parent / "credentials.json"


def get_drive_service():
    """
    Lay Google Drive service.
    Lan dau: Mo browser de user authorize (chi mot lan)
    Lan sau: Tu dong dung token da luu
    """
    creds = None
    
    # Kiem tra token da luu
    if TOKEN_FILE.exists():
        print("Tim thay token da luu, dang load...")
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    # Neu khong co token hoac token het han
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Token het han, dang refresh...")
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                print("\nKhong tim thay credentials.json!")
                print("\nHuong dan setup:")
                print("1. Vao https://console.cloud.google.com")
                print("2. Tao project moi")
                print("3. Bat Google Drive API")
                print("4. Tao OAuth 2.0 credentials (Desktop app)")
                print("5. Tai credentials.json ve thu muc webreel-ai-agent/")
                return None
            
            print("Dang mo browser de authorize...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        # Luu token
        TOKEN_FILE.parent.mkdir(exist_ok=True)
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
        print(f"Da luu token tai: {TOKEN_FILE}")
    
    return build('drive', 'v3', credentials=creds)


def list_files(service, max_results=10):
    """List files trong Google Drive."""
    results = service.files().list(
        pageSize=max_results,
        fields="files(id, name, mimeType, createdTime)"
    ).execute()
    
    items = results.get('files', [])
    
    if not items:
        print("Khong co file nao")
    else:
        print(f"\nTim thay {len(items)} files:")
        for item in items:
            print(f"  - {item['name']} ({item['mimeType']})")
    
    return items


def create_folder(service, folder_name):
    """Tao folder moi trong Google Drive."""
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    
    folder = service.files().create(
        body=file_metadata,
        fields='id, name'
    ).execute()
    
    print(f"\nDa tao folder: {folder['name']} (ID: {folder['id']})")
    return folder


def main():
    print("\n=============================================")
    print("GOOGLE DRIVE API EXAMPLE")
    print("=============================================\n")
    
    service = get_drive_service()
    
    if not service:
        return
    
    print("\n[SUCCESS] Da ket noi Google Drive API!")
    print("Khong bi bot detection, khong can browser automation\n")
    
    # List files
    print("Dang list files...")
    list_files(service)
    
    # Tao folder test
    print("\nBan co muon tao folder test khong? (y/n)")
    choice = input().strip().lower()
    
    if choice == 'y':
        create_folder(service, "Test Folder from API")
    
    print("\n=============================================")
    print("HOAN THANH!")
    print("=============================================")
    print("\nLan sau chay lai, khong can authorize nua")
    print(f"Token da luu tai: {TOKEN_FILE}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nLoi: {e}")
        import traceback
        traceback.print_exc()
