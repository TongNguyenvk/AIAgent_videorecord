"""
Script to find shared folders and get their IDs.
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

def find_shared_folders():
    """Find all folders shared with the Service Account."""
    
    service = get_drive_service()
    
    logger.info("=== Searching for shared folders ===\n")
    
    # Search for folders shared with me
    query = "mimeType='application/vnd.google-apps.folder' and sharedWithMe=true"
    
    results = service.files().list(
        q=query,
        fields="files(id, name, owners, shared, capabilities)",
        pageSize=20
    ).execute()
    
    items = results.get('files', [])
    
    if not items:
        logger.warning("No shared folders found!")
        logger.info("\nMake sure you:")
        logger.info("1. Shared the folder with the Service Account email")
        logger.info("2. Set permission to 'Editor'")
        logger.info("3. Wait a few seconds for changes to propagate")
        return None
    
    logger.info(f"Found {len(items)} shared folder(s):\n")
    
    webreel_folder = None
    
    for idx, item in enumerate(items, 1):
        logger.info(f"{idx}. {item['name']}")
        logger.info(f"   ID: {item['id']}")
        
        owners = item.get('owners', [])
        if owners:
            logger.info(f"   Owner: {owners[0].get('emailAddress', 'N/A')}")
        
        caps = item.get('capabilities', {})
        can_add = caps.get('canAddChildren', False)
        logger.info(f"   Can upload files: {can_add}")
        logger.info("")
        
        if 'webreel' in item['name'].lower() and 'presentation' in item['name'].lower():
            webreel_folder = item
    
    if webreel_folder:
        logger.info("="*60)
        logger.info("✓ Found WebReel_Presentations folder!")
        logger.info(f"Folder ID: {webreel_folder['id']}")
        logger.info("="*60)
        logger.info("\nUse this command to test upload:")
        logger.info(f"python test_gdrive_upload.py {webreel_folder['id']}")
        return webreel_folder['id']
    
    return None

if __name__ == "__main__":
    find_shared_folders()
