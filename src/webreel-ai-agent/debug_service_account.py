"""
Debug Service Account permissions and folder access.
"""

import sys
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from shared.google_drive_api import get_drive_service

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def debug_folder_access(folder_id: str):
    """Check if Service Account can access and write to the folder."""
    
    service = get_drive_service()
    
    logger.info(f"=== Debugging Folder Access ===")
    logger.info(f"Folder ID: {folder_id}\n")
    
    try:
        # Get folder info
        logger.info("Step 1: Getting folder info...")
        folder = service.files().get(
            fileId=folder_id,
            fields='id, name, owners, capabilities, permissions'
        ).execute()
        
        logger.info(f"✓ Folder found: {folder.get('name')}")
        
        owners = folder.get('owners', [])
        if owners:
            logger.info(f"  Owner: {owners[0].get('emailAddress')}")
        
        caps = folder.get('capabilities', {})
        logger.info(f"\nCapabilities:")
        logger.info(f"  Can add children (upload files): {caps.get('canAddChildren', False)}")
        logger.info(f"  Can edit: {caps.get('canEdit', False)}")
        logger.info(f"  Can delete: {caps.get('canDelete', False)}")
        
        if not caps.get('canAddChildren'):
            logger.error("\n✗ Service Account CANNOT upload files to this folder!")
            logger.info("The folder was not properly shared with Editor permission.")
            return False
        
        # Try to create a test file
        logger.info("\nStep 2: Testing file creation...")
        test_metadata = {
            'name': 'test_service_account.txt',
            'mimeType': 'text/plain',
            'parents': [folder_id]
        }
        
        from googleapiclient.http import MediaInMemoryUpload
        media = MediaInMemoryUpload(b'Test content from Service Account', mimetype='text/plain')
        
        test_file = service.files().create(
            body=test_metadata,
            media_body=media,
            fields='id, name'
        ).execute()
        
        logger.info(f"✓ Test file created: {test_file.get('name')}")
        logger.info(f"  File ID: {test_file.get('id')}")
        
        # Clean up test file
        logger.info("\nStep 3: Cleaning up test file...")
        service.files().delete(fileId=test_file.get('id')).execute()
        logger.info("✓ Test file deleted")
        
        logger.info("\n" + "="*60)
        logger.info("✓ SUCCESS: Service Account can upload to this folder!")
        logger.info("="*60)
        logger.info("\nThe folder is properly configured.")
        logger.info("The quota error might be a temporary Google API issue.")
        logger.info("\nTry running the upload test again:")
        logger.info(f"  python test_gdrive_upload.py {folder_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"\n✗ Error: {e}")
        
        if "403" in str(e):
            logger.error("\nPermission denied!")
            logger.info("Possible causes:")
            logger.info("1. Folder was not shared with Service Account")
            logger.info("2. Permission was set to 'Viewer' instead of 'Editor'")
            logger.info("3. Share link expired or was revoked")
        elif "404" in str(e):
            logger.error("\nFolder not found!")
            logger.info("The folder ID might be incorrect or the folder was deleted.")
        
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("Usage: python debug_service_account.py FOLDER_ID")
        logger.info("\nFolder ID: 1vrdUkiBsGVDZOyZtOCqoCypxAaBEPNgF")
        sys.exit(1)
    
    folder_id = sys.argv[1]
    success = debug_folder_access(folder_id)
    
    sys.exit(0 if success else 1)
