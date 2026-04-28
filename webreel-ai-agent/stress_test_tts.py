"""
Stress Test for TTS Concurrent Optimization

Tests Edge TTS with real-world narration data to measure:
- Success rate
- Total time
- Average time per segment
- Concurrent vs Sequential comparison

Usage:
    python stress_test_tts.py
"""
import sys
import time
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def stress_test():
    """Run stress test with real narration data."""
    print("=" * 80)
    print("TTS STRESS TEST - Edge TTS Concurrent Optimization")
    print("=" * 80)
    
    # Load real narration data (longer text)
    # Try multiple possible paths (local vs Docker)
    possible_paths = [
        Path(__file__).parent / "desktop_app" / "output" / "PHAN_6_narrations.json",
        Path(__file__).parent / "webreel-ai-agent" / "desktop_app" / "output" / "PHAN_6_narrations.json",
        Path("/app/webreel-ai-agent/desktop_app/output/PHAN_6_narrations.json"),
    ]
    
    narrations_file = None
    for p in possible_paths:
        if p.exists():
            narrations_file = p
            break
    
    if not narrations_file or not narrations_file.exists():
        print(f"❌ File not found in any of these locations:")
        for p in possible_paths:
            print(f"   - {p}")
        return
    
    with open(narrations_file, "r", encoding="utf-8") as f:
        texts = json.load(f)
    
    print(f"\n📝 Test Data:")
    print(f"   Segments: {len(texts)}")
    total_chars = sum(len(t) for t in texts)
    print(f"   Total characters: {total_chars:,}")
    print(f"   Average length: {total_chars // len(texts)} chars/segment")
    
    print("\n📋 Sample texts:")
    for i, text in enumerate(texts[:3]):
        preview = text[:70] + "..." if len(text) > 70 else text
        print(f"   {i+1}. {preview}")
    if len(texts) > 3:
        print(f"   ... and {len(texts) - 3} more")
    
    output_dir = Path(__file__).parent / "stress_test_output"
    output_dir.mkdir(exist_ok=True)
    
    # Test 1: Concurrent (Optimized)
    print("\n" + "=" * 80)
    print("TEST 1: CONCURRENT (Optimized - max 2 workers)")
    print("=" * 80)
    
    try:
        from shared.tts import generate_speech_batch
        
        start = time.time()
        segments = generate_speech_batch(
            texts=texts,
            output_dir=output_dir / "concurrent",
            voice="banmai",
            engine="edge",
        )
        elapsed_concurrent = time.time() - start
        
        success_rate = (len(segments) / len(texts)) * 100
        
        print("\n" + "=" * 80)
        print("✅ CONCURRENT RESULTS")
        print("=" * 80)
        print(f"Success rate: {len(segments)}/{len(texts)} ({success_rate:.1f}%)")
        print(f"Total time: {elapsed_concurrent:.2f}s")
        if segments:
            print(f"Average: {elapsed_concurrent/len(segments):.2f}s per segment")
            
            total_audio_ms = sum(seg.duration_ms for seg in segments)
            total_audio_s = total_audio_ms / 1000
            print(f"Total audio duration: {total_audio_s:.1f}s")
            print(f"Generation speed: {total_audio_s/elapsed_concurrent:.2f}x realtime")
        
        # Show file details
        if segments:
            print("\n📁 Generated files:")
            total_size = 0
            for seg in segments:
                size_kb = seg.audio_path.stat().st_size / 1024
                total_size += size_kb
                print(f"   {seg.audio_path.name}: {seg.duration_ms/1000:.1f}s ({size_kb:.1f} KB)")
            print(f"\n   Total size: {total_size:.1f} KB ({total_size/1024:.2f} MB)")
        
    except Exception as e:
        print(f"\n❌ CONCURRENT TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 2: Sequential (for comparison)
    print("\n" + "=" * 80)
    print("TEST 2: SEQUENTIAL (Old method - for comparison)")
    print("=" * 80)
    print("Generating one by one...")
    
    try:
        import edge_tts
        import asyncio
        
        async def generate_sequential():
            segments_seq = []
            voice = "vi-VN-HoaiMyNeural"
            
            for i, text in enumerate(texts):
                out_path = output_dir / "sequential" / f"segment_{i:03d}.mp3"
                out_path.parent.mkdir(exist_ok=True)
                
                try:
                    communicate = edge_tts.Communicate(text, voice, rate="+0%")
                    await communicate.save(str(out_path))
                    print(f"  [{i+1}/{len(texts)}] Generated {out_path.name}")
                    segments_seq.append(out_path)
                except Exception as e:
                    print(f"  [{i+1}/{len(texts)}] Failed: {e}")
            
            return segments_seq
        
        start = time.time()
        segments_seq = asyncio.run(generate_sequential())
        elapsed_sequential = time.time() - start
        
        print("\n" + "=" * 80)
        print("✅ SEQUENTIAL RESULTS")
        print("=" * 80)
        print(f"Success rate: {len(segments_seq)}/{len(texts)} ({len(segments_seq)/len(texts)*100:.1f}%)")
        print(f"Total time: {elapsed_sequential:.2f}s")
        if segments_seq:
            print(f"Average: {elapsed_sequential/len(segments_seq):.2f}s per segment")
        
    except Exception as e:
        print(f"\n❌ SEQUENTIAL TEST FAILED: {e}")
        elapsed_sequential = None
    
    # Comparison
    if elapsed_sequential:
        print("\n" + "=" * 80)
        print("📊 PERFORMANCE COMPARISON")
        print("=" * 80)
        print(f"Concurrent: {elapsed_concurrent:.2f}s")
        print(f"Sequential: {elapsed_sequential:.2f}s")
        speedup = elapsed_sequential / elapsed_concurrent
        time_saved = elapsed_sequential - elapsed_concurrent
        print(f"\n🚀 Speed up: {speedup:.2f}x faster")
        print(f"⏱️  Time saved: {time_saved:.2f}s ({time_saved/60:.1f} minutes)")
        print(f"💡 Efficiency: {(1 - elapsed_concurrent/elapsed_sequential)*100:.1f}% faster")
    
    print("\n" + "=" * 80)
    print("STRESS TEST COMPLETED!")
    print("=" * 80)
    print(f"Output directory: {output_dir}")

if __name__ == "__main__":
    stress_test()
