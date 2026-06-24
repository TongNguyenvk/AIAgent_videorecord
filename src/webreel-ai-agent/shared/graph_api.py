import msal
import requests
import os
import logging

logger = logging.getLogger("graph_api")

CLIENT_ID = os.getenv("MS_CLIENT_ID", "")
# Personal accounts must use 'consumers' or 'common'
AUTHORITY = "https://login.microsoftonline.com/consumers"
SCOPE = ["https://graph.microsoft.com/Files.ReadWrite.All"]

# Use absolute path for cache to avoid running context issues
WORKER_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_FILE = os.path.join(WORKER_DIR, "token_cache.bin")

def get_access_token():
    if not CLIENT_ID:
        raise ValueError("MS_CLIENT_ID missing in environment")

    # Initialize Cache
    cache = msal.SerializableTokenCache()
    if os.path.exists(CACHE_FILE):
        cache.deserialize(open(CACHE_FILE, "r").read())

    # PublicClientApplication for Delegated flows (like DeviceCodeFlow)
    app = msal.PublicClientApplication(
        CLIENT_ID, authority=AUTHORITY, token_cache=cache
    )

    result = None
    
    # 1. Silently acquire token from cache if possible
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPE, account=accounts[0])

    # 2. If empty cache or expired, initiate Device Code flow
    if not result:
        logger.info("No valid token in cache. Starting new interactive auth flow...")
        flow = app.initiate_device_flow(scopes=SCOPE)
        if "user_code" not in flow:
            raise ValueError(f"Could not initiate Device Flow: {flow}")
        
        # Print instruction to user for first-time login
        print("\n" + "="*80)
        print("BẮT BẬT Xác thực OneDrive!")
        print(flow["message"])
        print("="*80 + "\n")
        
        # Wait for user input
        result = app.acquire_token_by_device_flow(flow)

    # 3. Save cache and return
    if "access_token" in result:
        with open(CACHE_FILE, "w") as f:
            f.write(cache.serialize())
        return result["access_token"]
    else:
        raise Exception(f"Token acquisition failed: {result.get('error_description')}")

def upload_to_onedrive(file_path: str) -> str:
    """
    Uploads a file to the Personal OneDrive and returns the webUrl.
    If file is locked, adds timestamp to filename and retries.
    """
    import time
    
    token = get_access_token()
    original_file_name = os.path.basename(file_path)
    file_name = original_file_name
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/octet-stream'
    }

    # Endpoint explicitly locked to WebReel_Test_Ground on the logged-in personal account
    upload_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/WebReel_Test_Ground/{file_name}:/content"
    
    logger.info(f"Uploading file {file_name}...")
    
    # Try upload first
    with open(file_path, 'rb') as f:
        response = requests.put(upload_url, headers=headers, data=f)
    
    # If resource is locked, use timestamped filename
    if response.status_code == 423 or (response.status_code >= 400 and 'locked' in response.text.lower()):
        logger.warning(f"File {file_name} is locked. Using timestamped filename...")
        
        # Add timestamp to filename
        name_parts = os.path.splitext(original_file_name)
        timestamp = int(time.time())
        file_name = f"{name_parts[0]}_{timestamp}{name_parts[1]}"
        upload_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/WebReel_Test_Ground/{file_name}:/content"
        
        logger.info(f"Retrying upload with new filename: {file_name}")
        
        # Retry upload with new filename
        with open(file_path, 'rb') as f:
            response = requests.put(upload_url, headers=headers, data=f)
    
    if response.status_code in [200, 201]:
        drive_item = response.json()
        item_id = drive_item.get('id')
        web_url = drive_item.get('webUrl')
        parent_reference = drive_item.get('parentReference', {})
        drive_id = parent_reference.get('driveId')
        
        logger.info(f"Upload successful (ID: {item_id})")
        logger.info(f"Original webUrl: {web_url}")
        
        # Try multiple URL formats to find one that works
        # Format 1: Simple ID format (current)
        url_format_1 = f"https://onedrive.live.com/?id={item_id}"
        
        # Format 2: Edit mode format (may work better for presentations)
        url_format_2 = f"https://onedrive.live.com/edit.aspx?resid={item_id}"
        
        # Format 3: View mode format
        url_format_3 = f"https://onedrive.live.com/view.aspx?resid={item_id}"
        
        # Format 4: Use webUrl directly (SharePoint format)
        url_format_4 = web_url
        
        # Format 5: SlideShow format (Option 1)
        url_format_5 = f"https://onedrive.live.com/view.aspx?resid={item_id}&wdSlideShow=true"
        
        logger.info(f"URL Format 1 (ID): {url_format_1}")
        logger.info(f"URL Format 2 (Edit): {url_format_2}")
        logger.info(f"URL Format 3 (View): {url_format_3}")
        logger.info(f"URL Format 4 (WebUrl): {url_format_4}")
        logger.info(f"URL Format 5 (SlideShow): {url_format_5}")
        
        # Return SlideShow format for presentations
        return url_format_5
    else:
        logger.error(f"Upload error: {response.text}")
        raise Exception(f"OneDrive upload failed: {response.text}")

def delete_from_onedrive(file_name: str):
    """
    Cleans up the file from the personal OneDrive.
    """
    token = get_access_token()
    headers = {
        'Authorization': f'Bearer {token}'
    }

    delete_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/WebReel_Test_Ground/{file_name}"
    response = requests.delete(delete_url, headers=headers)
    
    if response.status_code == 204:
        logger.info(f"Successfully deleted {file_name} from OneDrive.")
    else:
        logger.error(f"Failed to delete {file_name}: {response.text}")
