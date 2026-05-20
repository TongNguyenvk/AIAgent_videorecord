import os
import logging
import time
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger("google_drive_api")

WORKER_DIR = Path(__file__).parent.parent
# Try webreel-ai-agent/key first, then fall back to root key/
SERVICE_ACCOUNT_FILE = WORKER_DIR / "key" / "webreel-495902-6cbaba75799d.json"
if not SERVICE_ACCOUNT_FILE.exists():
    # Fall back to root key/ directory
    SERVICE_ACCOUNT_FILE = WORKER_DIR.parent / "key" / "webreel-495902-6cbaba75799d.json"

SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_drive_service():
    """
    Get Google Drive service using Service Account (no user interaction required).
    """
    if not SERVICE_ACCOUNT_FILE.exists():
        raise FileNotFoundError(
            f"Service Account key file not found at {SERVICE_ACCOUNT_FILE}. "
            f"Please follow GOOGLE_DRIVE_SETUP.md to set it up."
        )
    
    credentials = service_account.Credentials.from_service_account_file(
        str(SERVICE_ACCOUNT_FILE),
        scopes=SCOPES
    )
    
    service = build('drive', 'v3', credentials=credentials, cache_discovery=False)
    return service

def get_or_create_folder(service, folder_name: str = "WebReel_Presentations") -> str:
    """
    Get or create a folder in Google Drive and return its ID.
    
    Args:
        service: Google Drive service instance
        folder_name: Name of the folder to create/find
        
    Returns:
        str: Folder ID
    """
    # Search for existing folder
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(
        q=query,
        spaces='drive',
        fields='files(id, name)'
    ).execute()
    
    items = results.get('files', [])
    
    if items:
        folder_id = items[0]['id']
        logger.info(f"Found existing folder '{folder_name}' with ID: {folder_id}")
        return folder_id
    
    # Create new folder if not found
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    
    folder = service.files().create(
        body=file_metadata,
        fields='id'
    ).execute()
    
    folder_id = folder.get('id')
    logger.info(f"Created new folder '{folder_name}' with ID: {folder_id}")
    
    return folder_id

def upload_to_gdrive(file_path: str, folder_id: str = None) -> dict:
    """
    Uploads a file to Google Drive, converts to Google Slides,
    makes it public (anyone with link can view), and returns dict with id and url.
    
    Args:
        file_path: Path to the PPTX file to upload
        folder_id: (Optional) Specific folder ID to upload to. If not provided,
                   will try to find or create WebReel_Presentations folder.
        
    Returns:
        dict: Contains 'file_id' and 'presentation_url'
    """
    service = get_drive_service()
    file_name = os.path.basename(file_path)
    
    # Use provided folder_id or get/create WebReel_Presentations folder
    if not folder_id:
        folder_id = get_or_create_folder(service)
    else:
        logger.info(f"Using provided folder ID: {folder_id}")
    
    # Upload and convert to Google Slides
    file_metadata = {
        'name': file_name,
        'mimeType': 'application/vnd.google-apps.presentation',
        'parents': [folder_id]
    }
    media = MediaFileUpload(
        file_path,
        mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation',
        resumable=True
    )
    
    logger.info(f"Uploading and converting {file_name} to Google Slides...")
    
    # Add retry logic
    file = None
    for attempt in range(3):
        try:
            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            break
        except Exception as e:
            logger.warning(f"Upload attempt {attempt+1} failed: {e}")
            if attempt < 2:
                time.sleep(2)
            else:
                raise e
    
    file_id = file.get('id')
    logger.info(f"Upload successful. File ID: {file_id}")
    
    # Set permissions to "anyone with link can view"
    logger.info("Setting file permissions to public (view only)...")
    permission = {
        'type': 'anyone',
        'role': 'reader'
    }
    service.permissions().create(
        fileId=file_id,
        body=permission,
        fields='id'
    ).execute()
    
    # Generate presentation URL
    present_url = f"https://docs.google.com/presentation/d/{file_id}/present"
    logger.info(f"Generated Presentation URL: {present_url}")
    
    return {
        "file_id": file_id,
        "presentation_url": present_url
    }

def delete_from_gdrive(file_id: str):
    """
    Deletes the file from Google Drive using its ID.
    """
    if not file_id:
        return
    try:
        service = get_drive_service()
        service.files().delete(fileId=file_id).execute()
        logger.info(f"Successfully deleted file ID {file_id} from Google Drive.")
    except Exception as e:
        logger.error(f"Failed to delete file ID {file_id}: {e}")
