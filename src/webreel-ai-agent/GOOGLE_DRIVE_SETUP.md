# Google Drive Setup Guide

This guide explains how to set up Google Drive API with Service Account for automated PPTX upload and conversion to Google Slides.

## Prerequisites

- Google Cloud Project with Drive API enabled
- Service Account created with appropriate permissions
- Service Account key file downloaded

## Step 1: Create Google Cloud Project (if not exists)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing project `webreel-495902`
3. Enable Google Drive API:
   - Go to **APIs & Services** > **Library**
   - Search for "Google Drive API"
   - Click **Enable**

## Step 2: Create Service Account

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **Service Account**
3. Fill in details:
   - **Service account name**: `webreel-service-account`
   - **Service account ID**: (auto-generated)
   - **Description**: Service account for WebReel automated uploads
4. Click **Create and Continue**
5. Skip role assignment (we'll use folder-level permissions)
6. Click **Done**

## Step 3: Generate Service Account Key

1. In **Credentials** page, find your service account
2. Click on the service account email
3. Go to **Keys** tab
4. Click **Add Key** > **Create new key**
5. Select **JSON** format
6. Click **Create**
7. Save the downloaded JSON file as:
   ```
   webreel-ai-agent/key/webreel-495902-6cbaba75799d.json
   ```

## Step 4: Create Folder Structure

Create the `key` directory if it doesn't exist:

```bash
cd webreel-ai-agent
mkdir key
```

Move the downloaded key file to this location:

```
webreel-ai-agent/
└── key/
    └── webreel-495902-6cbaba75799d.json
```

## Step 5: Share Google Drive Folder with Service Account

The Service Account needs access to upload files to your Google Drive.

### Option A: Share Specific Folder (Recommended)

1. Open [Google Drive](https://drive.google.com/)
2. Create a folder named `WebReel_Presentations` (or it will be auto-created)
3. Right-click the folder > **Share**
4. Add the Service Account email (found in the JSON key file under `client_email`):
   ```
   webreel-service-account@webreel-495902.iam.gserviceaccount.com
   ```
5. Set permission to **Editor**
6. Uncheck "Notify people"
7. Click **Share**

### Option B: Use Service Account's Own Drive

The Service Account has its own Google Drive space. Files uploaded will be in the Service Account's Drive, not your personal Drive. This is simpler but files won't appear in your personal Drive.

To access files:

- Use the Google Drive API to list files
- Or share individual files with your personal account after upload

## Step 6: Install Dependencies

Dependencies are already in `requirements.txt`:

```bash
pip install google-api-python-client google-auth
```

Or install all dependencies:

```bash
pip install -r requirements.txt
```

## Step 7: Test the Setup

Run the test script to verify everything works:

```bash
cd webreel-ai-agent
python test_gdrive_upload.py
```

The test will:

1. Upload a sample PPTX file
2. Convert it to Google Slides
3. Print the presentation URL
4. Wait for you to verify the URL works
5. Delete the file
6. Verify deletion

## Troubleshooting

### Error: Service Account key file not found

**Problem**: The key file is not in the correct location.

**Solution**:

- Verify the file path: `webreel-ai-agent/key/webreel-495902-6cbaba75799d.json`
- Check the filename matches exactly (including the project ID)

### Error: 403 Forbidden or Insufficient Permission

**Problem**: Service Account doesn't have permission to access Drive.

**Solution**:

- Verify you shared the `WebReel_Presentations` folder with the Service Account email
- Check the Service Account email in the JSON key file under `client_email`
- Make sure you gave **Editor** permission, not just **Viewer**

### Error: File not found after upload

**Problem**: File was uploaded to Service Account's Drive, not your personal Drive.

**Solution**:

- This is expected if you didn't share a folder (Option B above)
- Files are in the Service Account's own Drive space
- You can still access them via the API or by sharing them with your account

### Error: Cannot convert PPTX to Google Slides

**Problem**: The MIME type conversion failed.

**Solution**:

- Verify the PPTX file is valid (can be opened in PowerPoint)
- Check the file is not corrupted
- Try with a different PPTX file

## Security Notes

- **Never commit the Service Account key file to Git**
- The `key/` directory is already in `.gitignore`
- Keep the key file secure and don't share it publicly
- Rotate the key periodically for security

## API Quotas

Google Drive API has the following quotas (as of 2024):

- **Queries per day**: 1,000,000,000
- **Queries per 100 seconds per user**: 1,000

For WebReel's use case (uploading presentations), these limits are more than sufficient.

## Next Steps

After setup is complete:

- Run `test_gdrive_upload.py` to verify
- The module is ready to be integrated into `presentation_gg_worker` (Phase 2)
- See `GOOGLE_DRIVE_INTEGRATION_PRD.md` for the full implementation plan
