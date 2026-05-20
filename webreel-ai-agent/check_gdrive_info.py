"""
Script to check Google Drive account info and quota.
"""

import sys
import json
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from shared.google_drive_api import get_drive_service, SERVICE_ACCOUNT_FILE

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_account_info():
    """Check which account the Service Account is using."""
    
    logger.info("=== Google Drive Account Information ===\n")
    
    # 1. Check Service Account key file
    logger.info(f"Service Account Key File: {SERVICE_ACCOUNT_FILE}")
    
    if SERVICE_ACCOUNT_FILE.exists():
        with open(SERVICE_ACCOUNT_FILE, 'r') as f:
            key_data = json.load(f)
            logger.info(f"Service Account Email: {key_data.get('client_email')}")
            logger.info(f"Project ID: {key_data.get('project_id')}")
    else:
        logger.error("Key file not found!")
        return
    
    # 2. Get Drive service
    logger.info("\n=== Connecting to Google Drive ===")
    service = get_drive_service()
    
    # 3. Get account info (about)
    logger.info("\n=== Drive Storage Information ===")
    try:
        about = service.about().get(fields="user, storageQuota").execute()
        
        user = about.get('user', {})
        logger.info(f"User Display Name: {user.get('displayName', 'N/A')}")
        logger.info(f"User Email: {user.get('emailAddress', 'N/A')}")
        logger.info(f"User Permission ID: {user.get('permissionId', 'N/A')}")
        
        quota = about.get('storageQuota', {})
        limit = int(quota.get('limit', 0))
        usage = int(quota.get('usage', 0))
        usage_in_drive = int(quota.get('usageInDrive', 0))
        usage_in_trash = int(quota.get('usageInDriveTrash', 0))
        
        logger.info(f"\nStorage Quota:")
        logger.info(f"  Total Limit: {limit / (1024**3):.2f} GB")
        logger.info(f"  Total Usage: {usage / (1024**3):.2f} GB")
        logger.info(f"  Usage in Drive: {usage_in_drive / (1024**3):.2f} GB")
        logger.info(f"  Usage in Trash: {usage_in_trash / (1024**3):.2f} GB")
        logger.info(f"  Available: {(limit - usage) / (1024**3):.2f} GB")
        
        if usage >= limit:
            logger.error("\n⚠️  STORAGE QUOTA EXCEEDED!")
            logger.info("This is why uploads are failing.")
        else:
            logger.info(f"\n✓ Storage available: {(limit - usage) / (1024**3):.2f} GB")
            
    except Exception as e:
        logger.error(f"Failed to get storage info: {e}")
    
    # 4. List shared folders
    logger.info("\n=== Shared Folders (sharedWithMe) ===")
    try:
        results = service.files().list(
            q="mimeType='application/vnd.google-apps.folder' and sharedWithMe=true",
            fields="files(id, name, owners, shared, permissions)",
            pageSize=10
        ).execute()
        
        items = results.get('files', [])
        
        if not items:
            logger.info("No shared folders found.")
            logger.warning("\n⚠️  This might be the problem!")
            logger.info("The Service Account cannot see the shared folder.")
            logger.info("Please verify you shared 'WebReel_Presentations' with:")
            logger.info(f"  {key_data.get('client_email')}")
        else:
            logger.info(f"Found {len(items)} shared folder(s):\n")
            for item in items:
                logger.info(f"  - {item['name']}")
                logger.info(f"    ID: {item['id']}")
                owners = item.get('owners', [])
                if owners:
                    logger.info(f"    Owner: {owners[0].get('emailAddress', 'N/A')}")
                logger.info("")
                
    except Exception as e:
        logger.error(f"Failed to list shared folders: {e}")

if __name__ == "__main__":
    try:
        check_account_info()
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
