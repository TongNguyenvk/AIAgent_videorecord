"""
TTS Module - SIMPLIFIED VERSION (Pattern from os_recorder)

Simple, fast Edge TTS with asyncio.gather (NO Semaphore).
This is the correct way - let Edge TTS handle rate limiting internally.

Usage:
    from shared.tts_simple import generate_speech_batch_simple
    
    segments = generate_speech_batch_simple(
        texts=["text 1", "text 2", "text 3"],
        output_dir=Path("audio/"),
        voice="banmai"
    )
"""
import asyncio
import os
from pathlib import Path
from dataclasses import dataclass

@dataclass
class AudioSegment:
    text: str
    audio_path: Path
    start_time: float = 0.0
    duration_ms: int = 0


def measure_audio_duration_ms(audio_path: Path) -> int:
    """Measure audio duration using ffprobe."""
    try:
        import subprocess
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            duration_s = float(result.stdout.strip())
            return int(duration_s * 1000)
    except Exception:
        pass
    
    # Fallback
    try:
        from mutagen.mp3 import MP3
        audio = MP3(str(audio_path))
        return int(audio.info.length * 1000)
    except Exception:
        return 2000  # Default fallback


async def _generate_one_async(idx: int, text: str, output_path: Path, voice: str, rate: str) -> tuple[int, AudioSegment | None]:
    """Generate single TTS segment (async)."""
    if not text.strip():
        return idx, None
    
    try:
        import edge_tts
    except ImportError:
        raise ImportError("edge-tts not installed. Run: pip install edge-tts")
    
    # Retry logic (max 2 attempts)
    for attempt in range(2):
        try:
            if attempt > 0:
                await asyncio.sleep(1)  # Short delay on retry
            
            communicate = edge_tts.Communicate(text, voice, rate=rate)
            await communicate.save(str(output_path))
            
            duration_ms = measure_audio_duration_ms(output_path)
            seg = AudioSegment(text=text, audio_path=output_path, duration_ms=duration_ms)
            return idx, seg
        except Exception as e:
            if attempt == 0:
                print(f"  [TTS] Segment {idx} retry...")
            else:
                print(f"  [TTS WARN] Segment {idx} failed: {e}")
    
    return idx, None


def generate_speech_batch_simple(
    texts: list[str],
    output_dir: Path,
    voice: str = "banmai",
    speed: str = "",
) -> list[AudioSegment]:
    """
    Generate TTS for multiple texts using Edge TTS (SIMPLE & FAST).
    
    Pattern from os_recorder: asyncio.gather without Semaphore.
    Edge TTS handles rate limiting internally - no need for manual throttling.
    
    Args:
        texts: List of text strings
        output_dir: Directory to save MP3 files
        voice: Voice name (banmai/leminh/etc)
        speed: Speed adjustment
    
    Returns:
        List of AudioSegment objects (successful ones only)
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Voice mapping
    EDGE_VOICES = {
        "banmai": "vi-VN-HoaiMyNeural",
        "leminh": "vi-VN-NamMinhNeural",
        "myan": "vi-VN-HoaiMyNeural",
        "lannhi": "vi-VN-HoaiMyNeural",
        "linhsan": "vi-VN-HoaiMyNeural",
    }
    edge_voice = EDGE_VOICES.get(voice, "vi-VN-HoaiMyNeural")
    
    # Rate conversion
    rate = "+0%"
    if speed:
        try:
            speed_int = int(speed)
            rate = f"{speed_int * 10:+d}%"
        except ValueError:
            pass
    
    print(f"[TTS] Edge TTS (voice: {voice}) - PARALLEL (no limit, simple)")
    
    async def _generate_all():
        """Generate all TTS in parallel using asyncio.gather."""
        tasks = []
        for i, text in enumerate(texts):
            out_path = output_dir / f"segment_{i:03d}.mp3"
            tasks.append(_generate_one_async(i, text, out_path, edge_voice, rate))
        
        print(f"  Executing {len(tasks)} TTS requests in parallel...")
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    
    # Run async code
    try:
        # Check if already in event loop
        loop = asyncio.get_running_loop()
        # If yes, run in thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(lambda: asyncio.run(_generate_all()))
            results = future.result(timeout=300)
    except RuntimeError:
        # No event loop, run directly
        results = asyncio.run(_generate_all())
    
    # Process results
    segments = []
    for result in results:
        if isinstance(result, Exception):
            print(f"  [TTS ERROR] Task exception: {result}")
        elif result:
            idx, seg = result
            if seg:
                segments.append(seg)
                print(f"  [TTS] {idx+1}/{len(texts)}: '{seg.text[:50]}...' -> {seg.audio_path.name} ({seg.duration_ms}ms)")
    
    print(f"  Generated {len(segments)}/{len(texts)} segments successfully")
    return segments
