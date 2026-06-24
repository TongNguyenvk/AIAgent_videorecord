# PRD: Google Drive Upload Integration cho Presentation Worker

## 1. Tổng quan

Tích hợp Google Drive API vào `presentation_gg_worker` để upload file PPTX, convert sang Google Slides, và trình chiếu qua browser-use để quay video bài giảng tự động.

## 2. Vấn đề hiện tại

- `presentation_worker` hiện tại dùng OneDrive nhưng không ổn định khi trình chiếu với webreel
- Cần giải pháp thay thế ổn định hơn với Google Slides

## 3. Giải pháp

Sử dụng Google Drive API với Service Account để:

1. Upload file PPTX lên folder `WebReel_Presentations` trên Google Drive
2. Tự động convert sang Google Slides (native format)
3. Set quyền "Anyone with the link can view" để dễ truy cập
4. Trả về presentation URL cho browser-use
5. Cleanup sau khi hoàn thành

## 4. Chi tiết kỹ thuật

### 4.1. Authentication ✅ IMPLEMENTED

**Final Implementation: OAuth 2.0** (not Service Account)

**Rationale:**

- Service Account có quota = 0 GB (không có storage riêng)
- OAuth upload trực tiếp vào user's Drive (webreelworker@gmail.com)
- Token caching cho automated workflow

**Implementation:**

- **OAuth Client**: `client_secret_90225988307-*.json`
- **Scopes**: `https://www.googleapis.com/auth/drive.file`
- **Token Storage**: `output/google_oauth_token.pickle`
- **Auto-refresh**: Token tự động refresh khi expired

**Original Plan (Service Account):**

- ~~Method: Service Account (không cần user interaction)~~
- ~~Key file: `key/webreel-495902-6cbaba75799d.json`~~
- ~~Scopes: `https://www.googleapis.com/auth/drive.file`~~
- **Issue**: Service Account quota = 0 GB, không thể upload

### 4.2. Upload Flow ✅ IMPLEMENTED

**Implementation:**

1. Authenticate với OAuth 2.0 (token cached)
2. Tạo/kiểm tra folder `WebReel_Presentations` (nếu chưa có)
3. Upload PPTX với `mimeType='application/vnd.google-apps.presentation'` để tự động convert
4. Set permission "Anyone with the link can view" (role: reader)
5. Trả về presentation URL: `https://docs.google.com/presentation/d/{file_id}/present`

**Code:**

```python
from shared.google_drive_oauth import upload_to_gdrive_oauth

result = upload_to_gdrive_oauth("path/to/file.pptx")
# Returns: {"file_id": "...", "presentation_url": "..."}
```

**Features:**

- Retry logic (3 attempts) cho stability
- Auto-create folder nếu chưa tồn tại
- Error handling và logging đầy đủ
- Token auto-refresh (không cần login lại)

### 4.3. Cleanup ✅ IMPLEMENTED

- Xóa file khỏi Google Drive sau khi quay video xong
- Function: `delete_from_gdrive_oauth(file_id)`

### 4.4. Dependencies ✅ VERIFIED

All dependencies đã có trong `requirements.txt`:

- `google-api-python-client` ✓
- `google-auth` ✓
- `google-auth-httplib2` ✓
- `google-auth-oauthlib` ✓

## 5. Prompt Optimization cho Browser-Use

Cần tối ưu prompt để browser-use:

- Navigate đến Google Slides presentation mode
- Đợi slide load đầy đủ
- Sử dụng keyboard shortcuts (Space/ArrowRight) để chuyển slide
- Gọi `save_narration` cho mỗi slide
- Handle các edge cases (loading slow, authentication redirect)

## 6. Implementation Phases

### Phase 1: Setup Upload Flow ✅ COMPLETED (2026-05-10)

**Implementation Summary:**

**Authentication Method**: OAuth 2.0 (thay vì Service Account như ban đầu)

- Service Account có quota = 0 GB, không thể upload
- OAuth upload trực tiếp vào Drive của `webreelworker@gmail.com` (15 GB free)
- Token được cache và auto-refresh

**Files Created:**

- ✅ `shared/google_drive_oauth.py` - OAuth-based upload module
  - `get_drive_service_oauth()` - OAuth authentication với token caching
  - `get_or_create_folder_oauth()` - Tạo/lấy folder `WebReel_Presentations`
  - `upload_to_gdrive_oauth(file_path, folder_id=None)` - Upload & convert to Slides
  - `delete_from_gdrive_oauth(file_id)` - Cleanup
- ✅ `test_gdrive_oauth.py` - Test script (ALL TESTS PASSED)
- ✅ `output/google_oauth_token.pickle` - Cached OAuth token
- ✅ `GOOGLE_DRIVE_PHASE1_COMPLETE.md` - Detailed implementation summary

**Test Results:**

```
✓ Upload successful: test_slides.pptx → Google Slides
✓ File ID: 1STVv1gaeF_iTPN9-RtZAHOcE6w8ZjPNd49NzmqqoDBI
✓ Presentation URL: https://docs.google.com/presentation/d/.../present
✓ File verified: application/vnd.google-apps.presentation
✓ File deleted successfully
✓ All tests passed!
```

**Setup Requirements:**

- OAuth Client credentials: `key/client_secret_90225988307-*.json` ✓
- Test user added in Google Cloud Console: `webreelworker@gmail.com` ✓
- OAuth token cached for future use (no repeated login) ✓

**Key Decisions:**

1. **OAuth vs Service Account**: Chọn OAuth vì Service Account không có storage quota
2. **Token Caching**: Token được lưu và auto-refresh, chỉ cần login 1 lần
3. **Scope**: `drive.file` (chỉ access files do app tạo)
4. **Permission**: "Anyone with link can view" (reader role)

**Not Done in Phase 1** (moved to Phase 2):

- Tích hợp vào worker
- Tối ưu prompt cho browser-use

### Phase 2: Worker Integration (Future)

- Tích hợp `google_drive_api` vào `presentation_gg_worker`
- Tối ưu prompt cho Google Slides
- Testing end-to-end với browser-use

## 7. Tasks Breakdown

### ✅ Task 1: Setup Google Drive API Module (COMPLETED)

**Mục tiêu**: Tạo module OAuth-based upload

**Deliverables**:

- ✅ File `shared/google_drive_oauth.py` với:
  - Function `get_drive_service_oauth()` - OAuth authentication với token caching
  - Function `get_or_create_folder_oauth(service, folder_name)` - tạo/lấy folder ID
  - Function `upload_to_gdrive_oauth(file_path, folder_id=None)` - upload và convert
  - Function `delete_from_gdrive_oauth(file_id)` - cleanup
- ✅ Dependencies verified trong `requirements.txt`

**Test**: ✅ Module imported và authenticated thành công

### ✅ Task 2: Implement Upload Flow với Conversion (COMPLETED)

**Mục tiêu**: Upload PPTX, convert sang Google Slides, set permissions

**Deliverables**:

- ✅ Complete implementation của `upload_to_gdrive_oauth()`:
  - Upload file với `mimeType='application/vnd.google-apps.presentation'`
  - Set permission "Anyone with the link can view"
  - Trả về dict với `file_id` và `presentation_url`
- ✅ Complete implementation của `delete_from_gdrive_oauth()`

**Test**: ✅ Upload file PPTX thực tế, verify URL hoạt động

**Test Results**:

```
✓ Upload successful: test_slides.pptx
✓ File ID: 1STVv1gaeF_iTPN9-RtZAHOcE6w8ZjPNd49NzmqqoDBI
✓ Presentation URL verified
✓ File type: application/vnd.google-apps.presentation
```

### ✅ Task 3: Create Test Script (COMPLETED)

**Mục tiêu**: Script để test toàn bộ flow upload/delete

**Deliverables**:

- ✅ File `test_gdrive_oauth.py`:
  - Upload sample PPTX
  - Print presentation URL
  - Verify file tồn tại trên Drive
  - Delete file
  - Verify file đã bị xóa

**Test**: ✅ Script chạy thành công end-to-end (ALL TESTS PASSED)

### ✅ Task 4: Documentation và Setup Guide (COMPLETED)

**Mục tiêu**: Hướng dẫn setup OAuth cho team

**Deliverables**:

- ✅ File `GOOGLE_DRIVE_PHASE1_COMPLETE.md`:
  - OAuth setup instructions
  - Test user configuration
  - Token caching explanation
  - Troubleshooting guide
  - Why OAuth instead of Service Account

**Test**: ✅ Documentation complete và accurate

## 8. Success Criteria ✅ ALL MET

- ✅ Upload PPTX thành công lên Google Drive
- ✅ File được convert sang Google Slides format
- ✅ Presentation URL hoạt động và accessible
- ✅ Cleanup function xóa file thành công
- ✅ Automated workflow (OAuth token cached, no repeated login)

**Test Evidence:**

```
2026-05-10 13:48:49 - Upload successful. File ID: 1STVv1gaeF_iTPN9-RtZAHOcE6w8ZjPNd49NzmqqoDBI
2026-05-10 13:48:50 - Generated Presentation URL: https://docs.google.com/presentation/d/.../present
2026-05-10 13:48:51 - ✓ File verified: application/vnd.google-apps.presentation
2026-05-10 13:48:54 - ✓ File successfully deleted
2026-05-10 13:48:54 - === All tests passed! ===
```

---

## 9. Implementation Notes (Phase 1)

### Authentication Decision

**Original Plan**: Service Account
**Final Implementation**: OAuth 2.0

**Reason for Change**:

- Service Account có quota = 0 GB (không có storage)
- Không thể upload vào shared folders từ Gmail accounts
- OAuth upload trực tiếp vào user's Drive (15 GB free)

### Token Management

- Token saved to: `output/google_oauth_token.pickle`
- Auto-refreshes when expired (no manual intervention)
- Browser login chỉ cần 1 lần (hoặc khi token expires)
- For production: Consider encrypted storage or secrets manager

### Files Created

```
webreel-ai-agent/
├── shared/
│   └── google_drive_oauth.py          # OAuth-based upload module
├── output/
│   └── google_oauth_token.pickle      # Cached OAuth token
├── test_gdrive_oauth.py               # Test script (PASSED)
├── GOOGLE_DRIVE_PHASE1_COMPLETE.md    # Implementation summary
└── GOOGLE_DRIVE_INTEGRATION_PRD.md    # This file (updated)
```

### Next Steps

Phase 2 will integrate this upload flow into `presentation_gg_worker` and optimize browser-use prompts for Google Slides navigation.

---

**Phase 1 Status**: ✅ COMPLETED (2026-05-10)  
**Phase 2 Status**: 🔜 READY TO START
