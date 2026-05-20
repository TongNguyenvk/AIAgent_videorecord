"""
Script to list and clean up files in Service Account's Google Drive.
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

def list_all_files():
    """List all files in Service Account's Drive."""
    service = get_drive_service()
    
    logger.info("Fetching all files from Service Account's Drive...")
    
    results = service.files().list(
        pageSize=100,
        fields="files(id, name, mimeType, size, createdTime, trashed)",
        orderBy="createdTime desc"
    ).execute()
    
    items = results.get('files', [])
    
    if not items:
        logger.info("No files found.")
        return []
    
    logger.info(f"\nFound {len(items)} files:\n")
    
    total_size = 0
    for idx, item in enumerate(items, 1):
        size = int(item.get('size', 0))
        total_size += size
        size_mb = size / (1024 * 1024)
        
        print(f"{idx}. {item['name']}")
        print(f"   ID: {item['id']}")
        print(f"   Type: {item['mimeType']}")
        print(f"   Size: {size_mb:.2f} MB")
        print(f"   Created: {item.get('createdTime', 'N/A')}")
        print(f"   Trashed: {item.get('trashed', False)}")
        print()
    
    logger.info(f"Total storage used: {total_size / (1024 * 1024):.2f} MB")
    
    return items

def delete_all_files(files):
    """Delete all files from the list."""
    service = get_drive_service()
    
    logger.info(f"\nDeleting {len(files)} files...")
    
    deleted = 0
    failed = 0
    
    for item in files:
        try:
            service.files().delete(fileId=item['id']).execute()
            logger.info(f"✓ Deleted: {item['name']}")
            deleted += 1
        except Exception as e:
            logger.error(f"✗ Failed to delete {item['name']}: {e}")
            failed += 1
    
    logger.info(f"\nDeletion complete: {deleted} deleted, {failed} failed")

def main():
    logger.info("=== Google Drive Cleanup Tool ===\n")
    
    try:
        files = list_all_files()
        
        if not files:
            logger.info("Nothing to clean up.")
            return
        
        print("\n" + "="*60)
        response = input("\nDo you want to DELETE ALL these files? (yes/no): ").strip().lower()
        
        if response == 'yes':
            delete_all_files(files)
            logger.info("\n✓ Cleanup complete!")
        else:
            logger.info("Cleanup cancelled.")
    
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
