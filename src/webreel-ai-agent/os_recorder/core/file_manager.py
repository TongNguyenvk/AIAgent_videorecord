"""
File Manager Module for OS Recorder.

Handles file operations for OS recording jobs:
- Download files from remote URLs (R2/CDN)
- Create backups for state reset
- Cleanup old files
- Progress tracking and error handling

Author: OS Recorder Team
Date: May 12, 2026
"""

import os
import shutil
import logging
import requests
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime, timedelta
import hashlib

logger = logging.getLogger(__name__)


class FileManager:
    """
    Manages file operations for OS recording jobs.
    
    Features:
    - Download files from URLs with progress tracking
    - Create backups for state reset
    - Cleanup old files based on age
    - Validate file integrity
    """
    
    # Default upload directory
    DEFAULT_UPLOAD_DIR = Path("C:/webreel_uploads")
    
    # Default backup directory
    DEFAULT_BACKUP_DIR = Path("C:/webreel_backups")
    
    # Supported file extensions
    SUPPORTED_EXTENSIONS = {
        # Office files
        '.xlsx', '.xls', '.xlsm',  # Excel
        '.docx', '.doc',           # Word
        '.pptx', '.ppt',           # PowerPoint
        # Other files
        '.pdf', '.txt', '.csv',
        '.png', '.jpg', '.jpeg',
    }
    
    def __init__(
        self,
        upload_dir: Optional[Path] = None,
        backup_dir: Optional[Path] = None,
    ):
        """
        Initialize FileManager.
        
        Args:
            upload_dir: Directory for downloaded files (default: C:/webreel_uploads)
            backup_dir: Directory for backup files (default: C:/webreel_backups)
        """
        self.upload_dir = upload_dir or self.DEFAULT_UPLOAD_DIR
        self.backup_dir = backup_dir or self.DEFAULT_BACKUP_DIR
        
        # Create directories if not exist
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"FileManager initialized: upload_dir={self.upload_dir}, backup_dir={self.backup_dir}")
    
    def download_file(
        self,
        url: str,
        job_id: str,
        filename: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
        timeout: int = 300,
    ) -> Optional[Path]:
        """
        Download file from URL to local directory.
        
        Args:
            url: File URL (R2/CDN or any HTTP URL)
            job_id: Job UUID for organizing files
            filename: Custom filename (optional, extracted from URL if not provided)
            progress_callback: Callback function(downloaded_bytes, total_bytes)
            timeout: Download timeout in seconds (default: 300s = 5min)
        
        Returns:
            Path: Local file path or None if failed
        
        Example:
            >>> fm = FileManager()
            >>> path = fm.download_file(
            ...     url="https://cdn.example.com/uploads/data.xlsx",
            ...     job_id="abc-123",
            ...     progress_callback=lambda d, t: print(f"{d}/{t} bytes")
            ... )
            >>> print(path)
            C:/webreel_uploads/abc-123/data.xlsx
        """
        try:
            # Extract filename from URL if not provided
            if not filename:
                filename = url.split('/')[-1].split('?')[0]  # Remove query params
            
            # Validate extension
            ext = Path(filename).suffix.lower()
            if ext not in self.SUPPORTED_EXTENSIONS:
                logger.warning(f"Unsupported file extension: {ext} (file: {filename})")
            
            # Create job directory
            job_dir = self.upload_dir / job_id
            job_dir.mkdir(parents=True, exist_ok=True)
            
            # Local file path
            local_path = job_dir / filename
            
            # Check if file already exists
            if local_path.exists():
                logger.info(f"File already exists: {local_path}")
                return local_path
            
            # Download file
            logger.info(f"Downloading file: {url} -> {local_path}")
            
            response = requests.get(url, stream=True, timeout=timeout)
            response.raise_for_status()
            
            # Get total size
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0
            
            # Write to file with progress tracking
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        
                        # Progress callback
                        if progress_callback:
                            progress_callback(downloaded_size, total_size)
            
            # Verify file was written
            actual_size = local_path.stat().st_size
            if actual_size == 0:
                logger.error(f"Downloaded file is empty")
                local_path.unlink()  # Delete empty file
                return None
            
            # Verify size matches if Content-Length was provided
            if total_size > 0 and actual_size != total_size:
                logger.warning(f"File size mismatch: expected {total_size}, got {actual_size} (may be due to chunked encoding)")
                # Don't fail - some servers don't report accurate Content-Length
            
            logger.info(f"File downloaded successfully: {local_path} ({actual_size} bytes)")
            return local_path
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download file: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during download: {e}")
            return None
    
    def create_backup(
        self,
        file_path: Path,
        backup_name: Optional[str] = None,
    ) -> Optional[Path]:
        """
        Create backup copy of file for state reset.
        
        Args:
            file_path: Path to file to backup
            backup_name: Custom backup name (optional, auto-generated if not provided)
        
        Returns:
            Path: Backup file path or None if failed
        
        Example:
            >>> fm = FileManager()
            >>> backup = fm.create_backup(Path("C:/webreel_uploads/abc-123/data.xlsx"))
            >>> print(backup)
            C:/webreel_backups/data_20260512_143022.xlsx
        """
        try:
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return None
            
            # Generate backup name
            if not backup_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                stem = file_path.stem
                ext = file_path.suffix
                backup_name = f"{stem}_{timestamp}{ext}"
            
            # Backup path
            backup_path = self.backup_dir / backup_name
            
            # Copy file
            logger.info(f"Creating backup: {file_path} -> {backup_path}")
            shutil.copy2(file_path, backup_path)
            
            # Verify backup
            if not backup_path.exists():
                logger.error(f"Backup creation failed: {backup_path}")
                return None
            
            # Verify size
            original_size = file_path.stat().st_size
            backup_size = backup_path.stat().st_size
            if original_size != backup_size:
                logger.error(f"Backup size mismatch: original {original_size}, backup {backup_size}")
                backup_path.unlink()
                return None
            
            logger.info(f"Backup created successfully: {backup_path} ({backup_size} bytes)")
            return backup_path
            
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None
    
    def restore_from_backup(
        self,
        backup_path: Path,
        target_path: Path,
    ) -> bool:
        """
        Restore file from backup.
        
        Args:
            backup_path: Path to backup file
            target_path: Path to restore to
        
        Returns:
            bool: Success status
        
        Example:
            >>> fm = FileManager()
            >>> success = fm.restore_from_backup(
            ...     backup_path=Path("C:/webreel_backups/data_20260512_143022.xlsx"),
            ...     target_path=Path("C:/webreel_uploads/abc-123/data.xlsx")
            ... )
        """
        try:
            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_path}")
                return False
            
            # Delete target if exists
            if target_path.exists():
                target_path.unlink()
            
            # Copy backup to target
            logger.info(f"Restoring from backup: {backup_path} -> {target_path}")
            shutil.copy2(backup_path, target_path)
            
            # Verify restore
            if not target_path.exists():
                logger.error(f"Restore failed: {target_path}")
                return False
            
            logger.info(f"File restored successfully: {target_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore from backup: {e}")
            return False
    
    def cleanup_job_files(
        self,
        job_id: str,
        delete_backups: bool = False,
    ) -> bool:
        """
        Delete all files for a specific job.
        
        Args:
            job_id: Job UUID
            delete_backups: Also delete backup files (default: False)
        
        Returns:
            bool: Success status
        
        Example:
            >>> fm = FileManager()
            >>> fm.cleanup_job_files("abc-123")
        """
        try:
            # Delete upload directory
            job_dir = self.upload_dir / job_id
            if job_dir.exists():
                logger.info(f"Deleting job directory: {job_dir}")
                shutil.rmtree(job_dir)
            
            # Delete backups if requested
            if delete_backups:
                # Find backups for this job (contains job_id in name)
                for backup_file in self.backup_dir.glob(f"*{job_id}*"):
                    logger.info(f"Deleting backup: {backup_file}")
                    backup_file.unlink()
            
            logger.info(f"Cleanup completed for job: {job_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup job files: {e}")
            return False
    
    def cleanup_old_files(
        self,
        max_age_days: int = 1,
        dry_run: bool = False,
    ) -> dict:
        """
        Delete files older than specified age.
        
        Args:
            max_age_days: Maximum age in days (default: 1 day)
            dry_run: Only report what would be deleted (default: False)
        
        Returns:
            dict: Statistics (deleted_count, freed_bytes, errors)
        
        Example:
            >>> fm = FileManager()
            >>> stats = fm.cleanup_old_files(max_age_days=1)
            >>> print(f"Deleted {stats['deleted_count']} files, freed {stats['freed_bytes']} bytes")
        """
        stats = {
            'deleted_count': 0,
            'freed_bytes': 0,
            'errors': 0,
        }
        
        try:
            cutoff_time = datetime.now() - timedelta(days=max_age_days)
            
            # Cleanup upload directory
            for job_dir in self.upload_dir.iterdir():
                if not job_dir.is_dir():
                    continue
                
                # Check directory age
                dir_mtime = datetime.fromtimestamp(job_dir.stat().st_mtime)
                if dir_mtime < cutoff_time:
                    # Calculate size
                    dir_size = sum(f.stat().st_size for f in job_dir.rglob('*') if f.is_file())
                    
                    if dry_run:
                        logger.info(f"[DRY RUN] Would delete: {job_dir} ({dir_size} bytes)")
                    else:
                        logger.info(f"Deleting old directory: {job_dir} ({dir_size} bytes)")
                        shutil.rmtree(job_dir)
                        stats['freed_bytes'] += dir_size
                    
                    stats['deleted_count'] += 1
            
            # Cleanup backup directory
            for backup_file in self.backup_dir.iterdir():
                if not backup_file.is_file():
                    continue
                
                # Check file age
                file_mtime = datetime.fromtimestamp(backup_file.stat().st_mtime)
                if file_mtime < cutoff_time:
                    file_size = backup_file.stat().st_size
                    
                    if dry_run:
                        logger.info(f"[DRY RUN] Would delete: {backup_file} ({file_size} bytes)")
                    else:
                        logger.info(f"Deleting old backup: {backup_file} ({file_size} bytes)")
                        backup_file.unlink()
                        stats['freed_bytes'] += file_size
                    
                    stats['deleted_count'] += 1
            
            logger.info(f"Cleanup completed: deleted {stats['deleted_count']} items, freed {stats['freed_bytes']} bytes")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            stats['errors'] += 1
        
        return stats
    
    def get_file_info(self, file_path: Path) -> Optional[dict]:
        """
        Get file information.
        
        Args:
            file_path: Path to file
        
        Returns:
            dict: File info (size, modified_time, extension, etc.) or None
        """
        try:
            if not file_path.exists():
                return None
            
            stat = file_path.stat()
            
            return {
                'path': str(file_path),
                'name': file_path.name,
                'size_bytes': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'extension': file_path.suffix.lower(),
                'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'created_time': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Failed to get file info: {e}")
            return None
    
    def validate_file(self, file_path: Path) -> bool:
        """
        Validate file exists and is readable.
        
        Args:
            file_path: Path to file
        
        Returns:
            bool: True if valid
        """
        try:
            if not file_path.exists():
                logger.error(f"File does not exist: {file_path}")
                return False
            
            if not file_path.is_file():
                logger.error(f"Path is not a file: {file_path}")
                return False
            
            # Try to read first byte
            with open(file_path, 'rb') as f:
                f.read(1)
            
            return True
            
        except Exception as e:
            logger.error(f"File validation failed: {e}")
            return False


# Singleton instance
_file_manager_instance: Optional[FileManager] = None


def get_file_manager() -> FileManager:
    """
    Get singleton FileManager instance.
    
    Returns:
        FileManager: Singleton instance
    """
    global _file_manager_instance
    if _file_manager_instance is None:
        _file_manager_instance = FileManager()
    return _file_manager_instance
