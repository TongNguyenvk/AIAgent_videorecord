# Task 3: File Manager - Quick Reference

**Status:** ✅ PRODUCTION READY  
**Date:** May 12, 2026

---

## Quick Start

```python
from core.file_manager import get_file_manager

# Get singleton instance
fm = get_file_manager()

# Download file
local_path = fm.download_file(
    url="https://cdn.example.com/file.xlsx",
    job_id="job-123"
)

# Create backup
backup_path = fm.create_backup(local_path)

# Restore from backup
fm.restore_from_backup(backup_path, local_path)

# Cleanup
fm.cleanup_job_files("job-123")
```

---

## API Reference

### Download File

```python
local_path = fm.download_file(
    url: str,                    # File URL
    job_id: str,                 # Job UUID
    filename: Optional[str],     # Custom filename (optional)
    progress_callback: Optional[Callable],  # Progress callback
    timeout: int = 300           # Timeout in seconds
) -> Optional[Path]
```

### Create Backup

```python
backup_path = fm.create_backup(
    file_path: Path,             # File to backup
    backup_name: Optional[str]   # Custom backup name (optional)
) -> Optional[Path]
```

### Restore from Backup

```python
success = fm.restore_from_backup(
    backup_path: Path,           # Backup file
    target_path: Path            # Target file
) -> bool
```

### Cleanup Job Files

```python
success = fm.cleanup_job_files(
    job_id: str,                 # Job UUID
    delete_backups: bool = False # Also delete backups
) -> bool
```

### Cleanup Old Files

```python
stats = fm.cleanup_old_files(
    max_age_days: int = 1,       # Maximum age in days
    dry_run: bool = False        # Dry run mode
) -> dict  # {'deleted_count': int, 'freed_bytes': int, 'errors': int}
```

### Get File Info

```python
info = fm.get_file_info(
    file_path: Path              # File path
) -> Optional[dict]  # {'path', 'name', 'size_bytes', 'size_mb', 'extension', ...}
```

### Validate File

```python
valid = fm.validate_file(
    file_path: Path              # File path
) -> bool
```

---

## Directory Structure

```
C:/
├── webreel_uploads/          # Downloaded files
│   └── {job_id}/
│       └── {filename}
│
└── webreel_backups/          # Backup files
    └── {filename}_{timestamp}.{ext}
```

---

## Supported File Types

- Excel: `.xlsx`, `.xls`, `.xlsm`
- Word: `.docx`, `.doc`
- PowerPoint: `.pptx`, `.ppt`
- PDF: `.pdf`
- Text: `.txt`, `.csv`
- Images: `.png`, `.jpg`, `.jpeg`

---

## Error Handling

All methods return `None` or `False` on error and log the error message.

```python
local_path = fm.download_file(url="...", job_id="...")
if not local_path:
    print("Download failed, check logs")
```

---

## Testing

```bash
# Core tests
python test_file_manager.py

# Download tests (requires internet)
python test_file_manager_download.py
```

---

## Integration Example

```python
from core.file_manager import get_file_manager

def process_job(job_config):
    fm = get_file_manager()

    # Download file
    if job_config.uploaded_file_url:
        local_path = fm.download_file(
            url=job_config.uploaded_file_url,
            job_id=job_config.job_id,
            progress_callback=lambda d, t: print(f"{d}/{t}")
        )

        if not local_path:
            raise Exception("Download failed")

        # Create backup
        backup_path = fm.create_backup(local_path)

        # Process file...

        # Restore if needed
        if need_reset:
            fm.restore_from_backup(backup_path, local_path)

        # Cleanup
        if success:
            fm.cleanup_job_files(job_config.job_id)
```

---

## Performance

- **Download:** Depends on network speed
- **Backup:** <1s for files <10MB
- **Restore:** <1s for files <10MB
- **Cleanup:** <0.1s per file

---

## Troubleshooting

### Download fails

- Check URL is accessible
- Check network connection
- Increase timeout: `timeout=600`

### Backup fails

- Check file exists
- Check disk space
- Check permissions

### Cleanup doesn't work

- Check `dry_run=False`
- Check file age: `max_age_days=0` to delete all

---

## Files

- **Module:** `os_recorder/core/file_manager.py` (450 lines)
- **Tests:** `os_recorder/test_file_manager.py` (250 lines)
- **Download Tests:** `os_recorder/test_file_manager_download.py` (180 lines)
- **Documentation:** `os_recorder/TASK_3_FILE_MANAGER_SUMMARY.md`

---

## Summary

✅ **9/9 tests passed**  
✅ **Production ready**  
✅ **Fully documented**  
✅ **Error handling**  
✅ **Progress tracking**

**Ready for integration!**
