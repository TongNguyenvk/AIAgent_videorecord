"""
Media Engine - Xu ly am thanh (edge-tts) va quay man hinh (FFmpeg gdigrab).
"""

import asyncio
import subprocess
import logging
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# TTS: edge-tts
# ---------------------------------------------------------------------------
async def _generate_audio_async(
    text: str,
    output_mp3_path: str,
    voice: str = "vi-VN-HoaiMyNeural",
) -> str:
    """Generate Vietnamese TTS audio using edge-tts (async)."""
    import edge_tts

    Path(output_mp3_path).parent.mkdir(parents=True, exist_ok=True)

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_mp3_path)

    logger.info(f"Audio generated: {output_mp3_path}")
    return output_mp3_path


def generate_audio(
    text: str,
    output_mp3_path: str,
    voice: str = "vi-VN-HoaiMyNeural",
) -> str:
    """
    Tao audio tieng Viet tu text bang edge-tts.

    Args:
        text: Noi dung can doc.
        output_mp3_path: Duong dan file MP3 output.
        voice: Ten giong doc (mac dinh: Hoai My nu).

    Returns:
        Duong dan file MP3 da tao.
    """
    return asyncio.run(_generate_audio_async(text, output_mp3_path, voice))


# ---------------------------------------------------------------------------
# Audio duration: ffprobe
# ---------------------------------------------------------------------------
def get_audio_duration(mp3_path: str) -> int:
    """
    Lay do dai chinh xac cua file audio bang ffprobe.

    Args:
        mp3_path: Duong dan file audio.

    Returns:
        Do dai tinh bang milliseconds.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-show_entries", "format=duration",
                "-of", "csv=p=0",
                mp3_path,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode != 0:
            logger.error(f"ffprobe error: {result.stderr}")
            return 0

        duration_sec = float(result.stdout.strip())
        duration_ms = int(duration_sec * 1000)
        logger.info(f"Audio duration: {mp3_path} = {duration_ms}ms")
        return duration_ms

    except FileNotFoundError:
        logger.error("ffprobe not found. Please install FFmpeg and add to PATH.")
        return 0
    except Exception as e:
        logger.error(f"Failed to get audio duration: {e}")
        return 0


# ---------------------------------------------------------------------------
# Screen Recording: FFmpeg gdigrab
# ---------------------------------------------------------------------------
def start_screen_recording(
    target_pid: int,
    output_video_path: str,
    framerate: int = 30,
) -> subprocess.Popen | None:
    """
    Bat dau quay man hinh vung cua so bang FFmpeg gdigrab.

    Args:
        target_pid: PID cua cua so can quay.
        output_video_path: Duong dan file video output.
        framerate: So frame/giay (mac dinh 30).

    Returns:
        Process object cua FFmpeg, hoac None neu loi.
    """
    from core.window_manager import get_window_rect_by_pid

    rect = get_window_rect_by_pid(target_pid)
    if not rect:
        logger.error(f"Cannot find window with PID {target_pid}")
        return None

    left, top, width, height = rect

    # Dam bao width va height la so chan (yeu cau cua ffmpeg h264)
    width = width - (width % 2)
    height = height - (height % 2)

    Path(output_video_path).parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",                           # Ghi de file cu
        "-f", "gdigrab",                # Windows screen capture
        "-framerate", str(framerate),
        "-offset_x", str(left),
        "-offset_y", str(top),
        "-video_size", f"{width}x{height}",
        "-i", "desktop",                # Capture tu desktop
        "-c:v", "libx264",
        "-preset", "ultrafast",         # Nhanh nhat, it CPU
        "-pix_fmt", "yuv420p",
        "-tune", "zerolatency",
        "-movflags", "frag_keyframe+empty_moov",  # Fragmented MP4: luon playable du bi kill
        output_video_path,
    ]

    logger.info(f"Starting recording: {width}x{height} at ({left},{top})")
    logger.info(f"FFmpeg cmd: {' '.join(cmd)}")

    try:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # Cho FFmpeg khoi dong
        time.sleep(1)

        if process.poll() is not None:
            logger.error(f"FFmpeg exited immediately")
            return None

        logger.info(f"Recording started (PID={process.pid})")
        return process

    except FileNotFoundError:
        logger.error("FFmpeg not found. Please install FFmpeg and add to PATH.")
        return None
    except Exception as e:
        logger.error(f"Failed to start recording: {e}")
        return None


def stop_recording(process: subprocess.Popen) -> bool:
    """
    Dừng quay màn hình một cách graceful bằng cách gửi 'q' cho FFmpeg.

    Args:
        process: Process object của FFmpeg.

    Returns:
        True nếu dừng thành công.
    """
    if process is None or process.poll() is not None:
        logger.warning("FFmpeg process already stopped")
        return False

    try:
        # Gửi 'q\n' để FFmpeg dừng graceful (finalize moov atom)
        if process.stdin:
            process.stdin.write(b"q\n")
            process.stdin.flush()
            process.stdin.close()
        
        # Chờ tối đa 15 giây (FFmpeg cần thời gian finalize file)
        process.wait(timeout=15)
        logger.info("Recording stopped gracefully")
        return True

    except subprocess.TimeoutExpired:
        logger.warning("FFmpeg chưa dừng sau 15s, thử terminate...")
        try:
            process.terminate()
            process.wait(timeout=5)
            logger.info("FFmpeg terminated")
        except subprocess.TimeoutExpired:
            logger.warning("FFmpeg không terminate, killing...")
            process.kill()
        return True
    except Exception as e:
        logger.error(f"Error stopping recording: {e}")
        try:
            process.terminate()
            process.wait(timeout=3)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass
        return False


def start_fullscreen_recording(
    output_video_path: str,
    framerate: int = 30,
) -> subprocess.Popen | None:
    """
    Quay toan bo man hinh (khong can PID).

    Args:
        output_video_path: Duong dan file video output.
        framerate: So frame/giay.

    Returns:
        Process object cua FFmpeg.
    """
    Path(output_video_path).parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-f", "gdigrab",
        "-framerate", str(framerate),
        "-i", "desktop",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-tune", "zerolatency",
        output_video_path,
    ]

    logger.info(f"Starting fullscreen recording")

    try:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        time.sleep(1)

        if process.poll() is not None:
            stderr = process.stderr.read().decode() if process.stderr else ""
            logger.error(f"FFmpeg exited immediately: {stderr}")
            return None

        logger.info(f"Fullscreen recording started (PID={process.pid})")
        return process

    except FileNotFoundError:
        logger.error("FFmpeg not found. Please install FFmpeg and add to PATH.")
        return None
    except Exception as e:
        logger.error(f"Failed to start recording: {e}")
        return None
