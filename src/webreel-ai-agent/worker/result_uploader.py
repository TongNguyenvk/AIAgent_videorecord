"""
Result Uploader - Upload OS pipeline results to VPS API.

Features:
  - Multipart file upload (video, document, pdf)
  - Retry logic with exponential backoff
  - Progress logging
  - Automatic file cleanup after successful upload
  - Chunked upload for large files

Usage:
    from worker.result_uploader import upload_results
    
    success = upload_results(
        job_id="abc123",
        files={
            "video": "/path/to/video.mp4",
            "document": "/path/to/doc.docx",
            "pdf": "/path/to/doc.pdf"
        },
        api_url="https://your-vps:8000",
        api_key="your-secret-key"
    )
"""

import logging
import os
import time
from pathlib import Path
from typing import Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger("result_uploader")


class ResultUploader:
    """Upload OS pipeline results to VPS with retry logic."""

    def __init__(
        self,
        api_url: str,
        api_key: str,
        max_retries: int = 3,
        timeout: int = 300,
        chunk_size: int = 8192,
    ):
        """
        Initialize uploader.

        Args:
            api_url: Base API URL (e.g., https://your-vps:8000)
            api_key: Internal API key for authentication
            max_retries: Number of retry attempts (default: 3)
            timeout: Request timeout in seconds (default: 300)
            chunk_size: Upload chunk size in bytes (default: 8KB)
        """
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.max_retries = max_retries
        self.timeout = timeout
        self.chunk_size = chunk_size

        # Setup session with retry strategy
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy."""
        session = requests.Session()

        # Retry strategy: exponential backoff
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=2,  # 1s, 2s, 4s, 8s...
            status_forcelist=[408, 429, 500, 502, 503, 504],
            allowed_methods=["POST"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def upload_results(
        self,
        job_id: str,
        files: Dict[str, str],
        metadata: Optional[Dict] = None,
        cleanup: bool = True,
    ) -> bool:
        """
        Upload job results to VPS.

        Args:
            job_id: Job ID
            files: Dict of file types to paths, e.g.:
                   {"video": "/path/to/video.mp4", "document": "/path/to/doc.docx"}
            metadata: Optional metadata dict
            cleanup: Delete local files after successful upload (default: True)

        Returns:
            True if upload successful, False otherwise
        """
        logger.info(f"Uploading results for Job {job_id}")

        # Validate files exist
        validated_files = {}
        for file_type, file_path in files.items():
            if not file_path:
                continue

            path = Path(file_path)
            if not path.exists():
                logger.warning(f"File not found: {file_path}")
                continue

            file_size = path.stat().st_size
            logger.info(f"  {file_type}: {path.name} ({self._format_size(file_size)})")
            validated_files[file_type] = path

        if not validated_files:
            logger.error("No valid files to upload")
            return False

        # Prepare upload
        url = f"{self.api_url}/api/internal/upload-result"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        # Prepare multipart data
        multipart_files = {}
        for file_type, path in validated_files.items():
            multipart_files[file_type] = (
                path.name,
                open(path, "rb"),
                self._get_content_type(path),
            )

        # Add metadata
        data = {"job_id": job_id}
        if metadata:
            import json
            data["metadata"] = json.dumps(metadata)

        try:
            # Upload with progress tracking
            start_time = time.time()
            logger.info(f"Uploading to {url}")

            response = self.session.post(
                url,
                headers=headers,
                files=multipart_files,
                data=data,
                timeout=self.timeout,
            )

            elapsed = time.time() - start_time

            # Close file handles
            for f in multipart_files.values():
                f[1].close()

            # Check response
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Upload successful in {elapsed:.1f}s")
                logger.info(f"Response: {result.get('message', 'OK')}")

                # Cleanup local files
                if cleanup:
                    self._cleanup_files(validated_files)

                return True

            else:
                logger.error(f"Upload failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False

        except requests.exceptions.Timeout:
            logger.error(f"Upload timeout after {self.timeout}s")
            return False

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            return False

        except Exception as e:
            logger.error(f"Upload error: {e}", exc_info=True)
            return False

        finally:
            # Ensure all file handles are closed
            for f in multipart_files.values():
                try:
                    f[1].close()
                except Exception:
                    pass

    def _cleanup_files(self, files: Dict[str, Path]):
        """Delete local files after successful upload."""
        logger.info("Cleaning up local files...")
        for file_type, path in files.items():
            try:
                path.unlink()
                logger.info(f"  Deleted: {path.name}")
            except Exception as e:
                logger.warning(f"  Failed to delete {path.name}: {e}")

    def _get_content_type(self, path: Path) -> str:
        """Get MIME type for file."""
        suffix = path.suffix.lower()
        content_types = {
            ".mp4": "video/mp4",
            ".webm": "video/webm",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".pdf": "application/pdf",
        }
        return content_types.get(suffix, "application/octet-stream")

    def _format_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"


def upload_results(
    job_id: str,
    files: Dict[str, str],
    api_url: str,
    api_key: str,
    metadata: Optional[Dict] = None,
    cleanup: bool = True,
    max_retries: int = 3,
) -> bool:
    """
    Convenience function to upload results.

    Args:
        job_id: Job ID
        files: Dict of file types to paths
        api_url: Base API URL
        api_key: Internal API key
        metadata: Optional metadata dict
        cleanup: Delete local files after upload (default: True)
        max_retries: Number of retry attempts (default: 3)

    Returns:
        True if upload successful, False otherwise

    Example:
        success = upload_results(
            job_id="abc123",
            files={
                "video": "/path/to/video.mp4",
                "document": "/path/to/doc.docx",
                "pdf": "/path/to/doc.pdf"
            },
            api_url="https://your-vps:8000",
            api_key="your-secret-key"
        )
    """
    uploader = ResultUploader(
        api_url=api_url,
        api_key=api_key,
        max_retries=max_retries,
    )

    return uploader.upload_results(
        job_id=job_id,
        files=files,
        metadata=metadata,
        cleanup=cleanup,
    )
