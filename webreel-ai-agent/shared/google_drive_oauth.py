"""
Google Drive API with OAuth 2.0 (user authentication).
This uploads directly to the user's Drive, not Service Account.
"""

import os
import pickle
import logging
import time
from pathlib import Path

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

logger = logging.getLogger("google_drive_oauth")

WORKER_DIR = Path(__file__).parent.parent
# Try multiple locations for credentials file
CREDENTIALS_FILE = WORKER_DIR / "key" / "client_secret_90225988307-ka4d274h171he15cbvjvktp1n0od82mo.apps.googleusercontent.com.json"
if not CREDENTIALS_FILE.exists():
    CREDENTIALS_FILE = WORKER_DIR.parent / "key" / "client_secret_90225988307-ka4d274h171he15cbvjvktp1n0od82mo.apps.googleusercontent.com.json"

# Token file in mounted output directory
TOKEN_FILE = Path("/app/output/google_oauth_token.pickle")
if not TOKEN_FILE.parent.exists():
    TOKEN_FILE = WORKER_DIR / "output" / "google_oauth_token.pickle"

SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_drive_service_oauth():
    """
    Get Google Drive service using OAuth 2.0 (user authentication).
    This will open a browser for first-time authentication.
    """
    creds = None
    
    # Load existing token
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    # Refresh or get new token
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logger.info("Refreshing expired OAuth token...")
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"OAuth credentials file not found at {CREDENTIALS_FILE}. "
                    f"Please download OAuth client credentials from Google Cloud Console."
                )
            
            logger.info("Starting OAuth flow (browser will open)...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        # Save token for future use
        TOKEN_FILE.parent.mkdir(exist_ok=True, parents=True)
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
        logger.info(f"OAuth token saved to {TOKEN_FILE}")
    
    service = build('drive', 'v3', credentials=creds, cache_discovery=False)
    return service

def get_or_create_folder_oauth(service, folder_name: str = "WebReel_Presentations") -> str:
    """Get or create a folder in user's Google Drive."""
    
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
    
    # Create new folder
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

def upload_to_gdrive_oauth(file_path: str, folder_id: str = None) -> dict:
    """
    Upload file to Google Drive using OAuth (user's Drive).
    
    Args:
        file_path: Path to the PPTX file
        folder_id: Optional folder ID to upload to
        
    Returns:
        dict: Contains 'file_id' and 'presentation_url'
    """
    service = get_drive_service_oauth()
    file_name = os.path.basename(file_path)
    
    # Get or create folder
    if not folder_id:
        folder_id = get_or_create_folder_oauth(service)
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
    
    # Retry logic
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

def delete_from_gdrive_oauth(file_id: str):
    """Delete file from Google Drive using OAuth."""
    if not file_id:
        return
    try:
        service = get_drive_service_oauth()
        service.files().delete(fileId=file_id).execute()
        logger.info(f"Successfully deleted file ID {file_id} from Google Drive.")
    except Exception as e:
        logger.error(f"Failed to delete file ID {file_id}: {e}")
