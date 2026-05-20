"""
File handling utilities for OS Worker result uploads.

Provides validation and storage functions for video, document, and PDF files.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException

logger = logging.getLogger(__name__)

# File type whitelist
ALLOWED_EXTENSIONS = {
    "video": [".mp4", ".webm", ".avi", ".mov"],
    "document": [".docx", ".doc"],
    "pdf": [".pdf"]
}

# File size limits (in bytes)
MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB


def validate_file_type(filename: str, file_type: str) -> bool:
    """
    Validate file extension against whitelist.
    
    Args:
        filename: Name of the file
        file_type: Type category (video, document, pdf)
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not filename:
        return False
    
    ext = Path(filename).suffix.lower()
    allowed = ALLOWED_EXTENSIONS.get(file_type, [])
    
    return ext in allowed


def validate_file_size(file_size: int) -> bool:
    """
    Validate file size is within limit.
    
    Args:
        file_size: Size in bytes
        
    Returns:
        bool: True if valid, False otherwise
    """
    return 0 < file_size <= MAX_FILE_SIZE


def validate_job_id(job_id: str) -> bool:
    """
    Validate job_id format to prevent path traversal attacks.
    
    Args:
        job_id: Job UUID string
        
    Returns:
        bool: True if valid UUID format
    """
    import re
    # UUID format: 8-4-4-4-12 hex characters
    uuid_pattern = r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'
    return bool(re.match(uuid_pattern, job_id.lower()))


async def save_upload_file(
    upload_file: UploadFile,
    save_path: Path,
    max_size: int = MAX_FILE_SIZE
) -> Tuple[bool, Optional[str], int]:
    """
    Save uploaded file to disk with size validation.
    
    Args:
        upload_file: FastAPI UploadFile object
        save_path: Destination path
        max_size: Maximum allowed file size in bytes
        
    Returns:
        Tuple of (success, error_message, bytes_written)
    """
    try:
        # Ensure parent directory exists
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Read and write in chunks to handle large files
        bytes_written = 0
        chunk_size = 1024 * 1024  # 1MB chunks
        
        with open(save_path, "wb") as f:
            while True:
                chunk = await upload_file.read(chunk_size)
                if not chunk:
                    break
                
                bytes_written += len(chunk)
                
                # Check size limit
                if bytes_written > max_size:
                    # Delete partial file
                    f.close()
                    save_path.unlink(missing_ok=True)
                    return False, f"File too large (max {max_size // 1024 // 1024}MB)", 0
                
                f.write(chunk)
        
        logger.info(f"Saved file: {save_path} ({bytes_written} bytes)")
        return True, None, bytes_written
        
    except Exception as e:
        logger.error(f"Failed to save file {save_path}: {e}", exc_info=True)
        # Clean up partial file
        if save_path.exists():
            save_path.unlink(missing_ok=True)
        return False, f"Failed to save file: {str(e)}", 0


def get_output_directory(job_id: str, base_dir: str = "output") -> Path:
    """
    Get output directory path for a job.
    
    Args:
        job_id: Job UUID
        base_dir: Base output directory
        
    Returns:
        Path: Directory path for job outputs
    """
    return Path(base_dir) / job_id


def cleanup_job_directory(job_id: str, base_dir: str = "output") -> bool:
    """
    Delete all files in a job's output directory.
    
    Args:
        job_id: Job UUID
        base_dir: Base output directory
        
    Returns:
        bool: True if successful
    """
    try:
        job_dir = get_output_directory(job_id, base_dir)
        if job_dir.exists():
            import shutil
            shutil.rmtree(job_dir)
            logger.info(f"Cleaned up job directory: {job_dir}")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed to cleanup job directory {job_id}: {e}")
        return False
