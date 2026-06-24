"""
Script to set up shared folder permissions for Service Account.

This script adds the Service Account as an editor to a specific folder,
allowing it to upload files that will use the folder owner's quota.
"""

import sys
import json
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from google.oauth2 import service_account
from googleapiclient.discovery import build

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Service Account credentials
WORKER_DIR = Path(__file__).parent
SERVICE_ACCOUNT_FILE = WORKER_DIR.parent / "key" / "webreel-495902-6cbaba75799d.json"
if not SERVICE_ACCOUNT_FILE.exists():
    SERVICE_ACCOUNT_FILE = WORKER_DIR / "key" / "webreel-495902-6cbaba75799d.json"

SCOPES = ['https://www.googleapis.com/auth/drive']

def get_service_account_email():
    """Get Service Account email from key file."""
    with open(SERVICE_ACCOUNT_FILE, 'r') as f:
        key_data = json.load(f)
        return key_data.get('client_email')

def add_service_account_to_folder(folder_id: str):
    """
    Add Service Account as editor to a folder.
    
    NOTE: This requires the folder to be owned by a Google Workspace account
    OR you need to use OAuth to authenticate as the folder owner.
    
    For Gmail accounts, you MUST share manually through the Drive UI.
    """
    
    sa_email = get_service_account_email()
    logger.info(f"Service Account Email: {sa_email}")
    logger.info(f"Target Folder ID: {folder_id}")
    
    # Try to add permission using Service Account credentials
    credentials = service_account.Credentials.from_service_account_file(
        str(SERVICE_ACCOUNT_FILE),
        scopes=SCOPES
    )
    
    service = build('drive', 'v3', credentials=credentials, cache_discovery=False)
    
    try:
        # Try to get folder info first
        folder = service.files().get(fileId=folder_id, fields='id, name, owners').execute()
        logger.info(f"Folder found: {folder.get('name')}")
        
        owners = folder.get('owners', [])
        if owners:
            logger.info(f"Folder owner: {owners[0].get('emailAddress')}")
        
        # Try to add permission
        permission = {
            'type': 'user',
            'role': 'writer',
            'emailAddress': sa_email
        }
        
        result = service.permissions().create(
            fileId=folder_id,
            body=permission,
            fields='id'
        ).execute()
        
        logger.info(f"✓ Successfully added Service Account to folder!")
        logger.info(f"Permission ID: {result.get('id')}")
        
    except Exception as e:
        logger.error(f"✗ Failed to add permission: {e}")
        logger.info("\n" + "="*60)
        logger.info("MANUAL SHARING REQUIRED")
        logger.info("="*60)
        logger.info("\nService Account cannot add itself to Gmail folders.")
        logger.info("You must share the folder manually:")
        logger.info("\n1. Open Google Drive: https://drive.google.com")
        logger.info("2. Find folder 'WebReel_Presentations'")
        logger.info("3. Right-click > Share")
        logger.info(f"4. Add this email: {sa_email}")
        logger.info("5. Set permission to 'Editor'")
        logger.info("6. Uncheck 'Notify people'")
        logger.info("7. Click 'Share'")
        logger.info("\nAfter sharing, run: python test_gdrive_upload.py FOLDER_ID")

def main():
    logger.info("=== Google Drive Folder Setup ===\n")
    
    if len(sys.argv) < 2:
        logger.error("Usage: python setup_shared_folder.py FOLDER_ID")
        logger.info("\nTo get FOLDER_ID:")
        logger.info("1. Open the folder in Google Drive")
        logger.info("2. Copy the ID from URL: https://drive.google.com/drive/folders/FOLDER_ID")
        sys.exit(1)
    
    folder_id = sys.argv[1]
    add_service_account_to_folder(folder_id)

if __name__ == "__main__":
    main()
