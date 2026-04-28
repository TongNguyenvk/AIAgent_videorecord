"""
Quick Test - Fixed Pipeline

Simple script to quickly test the fixed pipeline with a minimal task.

USAGE:
    python quick_test_fixed.py
"""

import asyncio
from run_pipeline_unified_chrome_fixed import run_unified_pipeline_fixed


async def main():
    print("Quick Test - Fixed Audio Sync Pipeline")
    print("="*60)
    
    # Simple task
    task = "vào w3school tìm kiếm python và bắt đầu khóa học"
    video_name = "quick_test_fixed"
    
    print(f"\nTask: {task}")
    print(f"Video name: {video_name}")
    print("\nStarting pipeline...")
    print("="*60)
    
    video_path = await run_unified_pipeline_fixed(
        task=task,
        video_name=video_name,
        enable_tts=True,
        tts_voice="banmai"
    )
    
    if video_path:
        print("\n" + "="*60)
        print("SUCCESS!")
        print("="*60)
        print(f"Video: {video_path}")
    else:
        print("\n" + "="*60)
        print("FAILED!")
        print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
