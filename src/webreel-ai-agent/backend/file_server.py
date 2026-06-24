"""
File Server - Upload PPTX to S3/R2 and generate presigned URLs.

Used by the Office Viewer pipeline:
  1. User uploads .pptx file
  2. Backend stores it in S3/R2
  3. Backend generates a presigned URL (expires in 1 hour)
  4. Worker opens the URL in view.officeapps.live.com for recording

Supports:
  - Cloudflare R2 (S3-compatible, cheaper)
  - AWS S3
  - Local file serving (development fallback)
"""

import hashlib
import hmac
import logging
import os
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Try to import boto3 for S3/R2 support
try:
    import boto3
    from botocore.config import Config as BotoConfig
    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False
    logger.info("boto3 not installed. Using local file serving for uploads.")


class FileServer:
    """Manages file uploads and presigned URL generation."""

    def __init__(self):
        self.endpoint = os.getenv("S3_ENDPOINT")
        self.access_key = os.getenv("S3_ACCESS_KEY")
        self.secret_key = os.getenv("S3_SECRET_KEY")
        self.bucket = os.getenv("S3_BUCKET", "webreel-uploads")
        self.public_url = os.getenv("S3_PUBLIC_URL")
        self.secret = os.getenv("SECRET_KEY", "dev-secret-key")

        self._s3_client = None
        self._local_dir = Path(__file__).parent.parent / "uploads"

    @property
    def is_s3_configured(self) -> bool:
        """Check if S3/R2 is properly configured."""
        return bool(S3_AVAILABLE and self.endpoint and self.access_key and self.secret_key)

    @property
    def s3(self):
        """Lazy S3 client initialization."""
        if self._s3_client is None and self.is_s3_configured:
            self._s3_client = boto3.client(
                "s3",
                endpoint_url=self.endpoint,
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                config=BotoConfig(signature_version="s3v4"),
            )
            logger.info(f"S3 client connected: {self.endpoint}")
        return self._s3_client

    async def upload_file(self, file_content: bytes, filename: str) -> dict:
        """Upload file and return access info.
        
        Returns:
            dict with keys: file_id, url, viewer_url, expires_in
        """
        # Generate unique file ID
        file_hash = hashlib.md5(file_content).hexdigest()[:8]
        timestamp = int(time.time())
        file_id = f"{timestamp}_{file_hash}_{filename}"

        if self.is_s3_configured:
            return await self._upload_to_s3(file_content, file_id, filename)
        else:
            return await self._save_local(file_content, file_id, filename)

    async def _upload_to_s3(self, content: bytes, file_id: str, filename: str) -> dict:
        """Upload to S3/R2 and generate presigned URL."""
        s3_key = f"uploads/{file_id}"

        self.s3.put_object(
            Bucket=self.bucket,
            Key=s3_key,
            Body=content,
            ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )

        # Generate presigned URL (1 hour expiry)
        presigned_url = self.s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": s3_key},
            ExpiresIn=3600,
        )

        # If public URL is configured, replace endpoint
        if self.public_url:
            from urllib.parse import urlparse
            parsed = urlparse(presigned_url)
            presigned_url = presigned_url.replace(
                f"{parsed.scheme}://{parsed.netloc}",
                self.public_url.rstrip("/"),
            )

        # Build Office Viewer URL
        from urllib.parse import quote
        viewer_url = f"https://view.officeapps.live.com/op/view.aspx?src={quote(presigned_url, safe='')}"

        logger.info(f"File uploaded to S3: {s3_key}")

        return {
            "file_id": file_id,
            "s3_key": s3_key,
            "url": presigned_url,
            "viewer_url": viewer_url,
            "expires_in": 3600,
            "storage": "s3",
        }

    async def _save_local(self, content: bytes, file_id: str, filename: str) -> dict:
        """Save file locally (development fallback).
        
        Note: Office Viewer cannot access localhost files.
        This mode is for testing upload logic only.
        """
        self._local_dir.mkdir(parents=True, exist_ok=True)
        file_path = self._local_dir / file_id

        with open(file_path, "wb") as f:
            f.write(content)

        # Generate a signed local URL
        signature = self._sign_url(file_id)
        local_url = f"/uploads/{file_id}?sig={signature}"

        logger.info(f"File saved locally: {file_path}")
        logger.warning("Local file serving mode. Office Viewer will NOT work. Configure S3/R2 for production.")

        return {
            "file_id": file_id,
            "url": local_url,
            "viewer_url": f"[LOCAL MODE] Office Viewer requires public URL. Configure S3_ENDPOINT in .env",
            "expires_in": 3600,
            "storage": "local",
        }

    def _sign_url(self, file_id: str, expires: int = 3600) -> str:
        """Create HMAC signature for local file URL."""
        expire_time = int(time.time()) + expires
        message = f"{file_id}:{expire_time}"
        sig = hmac.new(
            self.secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()
        return f"{sig}:{expire_time}"

    def verify_signature(self, file_id: str, signature: str) -> bool:
        """Verify HMAC signature for local file download."""
        try:
            sig, expire_time_str = signature.rsplit(":", 1)
            expire_time = int(expire_time_str)

            if time.time() > expire_time:
                return False

            message = f"{file_id}:{expire_time}"
            expected = hmac.new(
                self.secret.encode(),
                message.encode(),
                hashlib.sha256,
            ).hexdigest()

            return hmac.compare_digest(sig, expected)
        except Exception:
            return False


# Singleton
file_server = FileServer()
