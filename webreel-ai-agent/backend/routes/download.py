"""
Download routes for job result files.

Users can download video, document, and PDF files from completed jobs.
Requires user ownership verification.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pathlib import Path
import logging

from backend.auth import get_current_user
from backend.crud.jobs import get_job
from backend.utils.file_handler import get_output_directory

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["Downloads"])


@router.get("/{job_id}/download/{file_type}")
async def download_file(
    job_id: str,
    file_type: str,
    user: dict = Depends(get_current_user)
):
    """
    Download result file from completed job.
    
    Users can only download files from their own jobs.
    
    Args:
        job_id: Job UUID
        file_type: Type of file to download (video, document, pdf)
        user: Current authenticated user
        
    Returns:
        FileResponse: File download with proper headers
        
    Raises:
        HTTPException: 403, 404, 400 for various errors
    """
    # Validate file_type
    valid_types = ["video", "document", "pdf"]
    if file_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file_type. Must be one of: {', '.join(valid_types)}"
        )
    
    # Get job from MongoDB
    job = await get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )
    
    # Check ownership
    job_user_id = job.get("user_id")
    if job_user_id != user["user_id"]:
        logger.warning(
            f"User {user['user_id']} attempted to download file from job {job_id} owned by {job_user_id}"
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: not your job"
        )
    
    # Check if job is completed
    if job.get("status") != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job not completed yet (status: {job.get('status')})"
        )
    
    # Get file path from result
    result = job.get("result", {})
    file_path_key = f"{file_type}_path"
    file_path_str = result.get(file_path_key)
    
    # For video files, also check for R2 CDN URL
    video_url = result.get("video_url") if file_type == "video" else None
    
    if not file_path_str and not video_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{file_type.capitalize()} file not available for this job"
        )
    
    # If local file path exists, try to serve it
    if file_path_str:
        file_path = Path(file_path_str)
        
        if file_path.exists():
            # Determine media type
            media_types = {
                "video": "video/mp4",
                "document": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "pdf": "application/pdf"
            }
            media_type = media_types.get(file_type, "application/octet-stream")
            
            # Return file with download header
            logger.info(f"User {user['user_id']} downloading {file_type} from job {job_id}")
            
            return FileResponse(
                path=file_path,
                media_type=media_type,
                filename=file_path.name,
                headers={
                    "Content-Disposition": f'attachment; filename="{file_path.name}"'
                }
            )
    
    # Fallback: proxy from R2 CDN for video files
    if video_url and video_url.startswith("http"):
        import httpx
        from fastapi.responses import StreamingResponse
        
        url_filename = video_url.rsplit("/", 1)[-1] if "/" in video_url else f"{job_id}.mp4"
        
        try:
            async with httpx.AsyncClient(timeout=300.0, follow_redirects=True) as client:
                r2_response = await client.get(video_url)
                
                if r2_response.status_code != 200:
                    logger.error(f"R2 proxy failed: {r2_response.status_code} for {video_url}")
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Failed to fetch video from storage (status {r2_response.status_code})"
                    )
                
                content_length = r2_response.headers.get("content-length")
                headers = {
                    "Content-Disposition": f'attachment; filename="{url_filename}"',
                }
                if content_length:
                    headers["Content-Length"] = content_length
                
                logger.info(f"User {user['user_id']} downloading {file_type} from R2 for job {job_id}")
                
                return StreamingResponse(
                    content=iter([r2_response.content]),
                    media_type="video/mp4",
                    headers=headers,
                )
        except httpx.TimeoutException:
            raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail="Timeout fetching video from storage")
        except httpx.RequestError as e:
            logger.error(f"R2 proxy error: {e}")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to connect to video storage")
    
    logger.error(f"File not found on disk: {file_path_str}")
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{file_type.capitalize()} file not found on server"
    )

