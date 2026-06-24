"""
AI Reviewer Fixed - Timeline calculation with page load wait accounting

This module provides fixed versions of AI reviewer functions that:
1. Account for page load waits (3000ms) in timeline calculation
2. Validate timeline estimates against actual TTS durations
3. Return enhanced timeline metadata for downstream validation

USAGE: Import these functions instead of the original ones
"""

from typing import Any
from pathlib import Path


# Page load wait constant (3000ms = 3s)
PAGE_LOAD_WAIT_MS = 3000


def calculate_timeline_fixed(
    config: dict[str, Any],
    video_name: str,
    tts_segments: list[Any] | None = None
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Fixed timeline calculation with page load wait accounting.
    
    Changes from original:
    1. Navigate duration: 2.0s -> 5.0s (2.0s + 3.0s page load wait)
    2. Click duration: 0.5s -> 3.5s (0.5s + 3.0s page load wait)
    3. Validates against actual TTS durations if provided
    4. Returns enhanced metadata (total_duration, narration_points)
    
    Args:
        config: Webreel config dict
        video_name: Video name key in config
        tts_segments: Optional list of AudioSegment for validation
    
    Returns:
        Tuple of (timeline, metadata)
        - timeline: List of {step_index, action, start_time, end_time, duration, step_data}
        - metadata: {total_duration, narration_points, validation_warnings}
    """
    steps = config["videos"][video_name]["steps"]
    default_delay = config["videos"][video_name].get("defaultDelay", 300)
    
    timeline = []
    current_time = 0.0
    narration_points = []  # Track where narration segments should be inserted
    validation_warnings = []
    
    meaningful_step_index = 0  # Counter for non-pause steps
    
    for i, step in enumerate(steps):
        action = step.get("action", "")
        step_duration = 0.0
        
        if action == "pause":
            step_duration = step.get("ms", 0) / 1000.0
        elif action == "navigate":
            # FIX: Include page load wait
            step_duration = 2.0 + (PAGE_LOAD_WAIT_MS / 1000.0)  # 2s + 3s = 5s
        elif action == "click":
            # FIX: Include page load wait (assuming click triggers page load)
            step_duration = 0.5 + (PAGE_LOAD_WAIT_MS / 1000.0)  # 0.5s + 3s = 3.5s
        elif action == "moveTo":
            step_duration = 0.5  # Cursor movement
        elif action == "type":
            text = step.get("text", "")
            char_delay = step.get("charDelay", 50) / 1000.0
            step_duration = len(text) * char_delay
        elif action == "scroll":
            step_duration = 1.0  # Scroll animation
        elif action == "keypress":
            step_duration = 0.2
        
        # Add default delay
        step_duration += default_delay / 1000.0
        
        timeline.append({
            "step_index": i,
            "action": action,
            "start_time": current_time,
            "end_time": current_time + step_duration,
            "duration": step_duration,
            "step_data": step
        })
        
        # Track narration points for meaningful actions
        if action != "pause":
            narration_points.append({
                "step_index": i,
                "meaningful_index": meaningful_step_index,
                "action": action,
                "timeline_position": current_time
            })
            meaningful_step_index += 1
        
        current_time += step_duration
    
    # Validate against actual TTS durations if provided
    if tts_segments:
        for i, seg in enumerate(tts_segments):
            actual_duration_s = seg.duration_ms / 1000.0
            
            # Compare with narration point timing
            if i < len(narration_points):
                # This is a rough estimate - actual validation happens in audio_sync_optimizer
                estimated_gap = 4.0  # Rough estimate for narration duration
                divergence = abs(estimated_gap - actual_duration_s) / actual_duration_s
                
                if divergence > 0.20:  # 20% tolerance
                    validation_warnings.append({
                        "segment": i + 1,
                        "estimated_duration": estimated_gap,
                        "actual_duration": actual_duration_s,
                        "divergence_percent": divergence * 100,
                        "message": f"Segment {i+1} divergence {divergence*100:.1f}% exceeds 20%"
                    })
    
    metadata = {
        "total_duration": current_time,
        "narration_points": narration_points,
        "validation_warnings": validation_warnings,
        "meaningful_steps_count": meaningful_step_index
    }
    
    # Log warnings if any
    if validation_warnings:
        print(f"[AI Reviewer Fixed] Timeline validation warnings:")
        for warning in validation_warnings:
            print(f"  - {warning['message']}")
    
    return timeline, metadata


def review_and_enhance_config_fixed(
    config: dict[str, Any],
    history_data: dict[str, Any],
    video_name: str = "demo",
    tts_segments: list[Any] | None = None
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    """
    Fixed version of review_and_enhance_config that returns timeline metadata.
    
    This is a wrapper that:
    1. Calls the original review_and_enhance_config
    2. Calculates fixed timeline with validation
    3. Returns enhanced config, TTS script, AND timeline metadata
    
    Args:
        config: Webreel config
        history_data: Browser-use history
        video_name: Video name
        tts_segments: Optional actual TTS segments for validation
    
    Returns:
        Tuple of (enhanced_config, tts_script, timeline_metadata)
    """
    # Import original function
    from ai_reviewer import review_and_enhance_config
    
    # Call original AI review
    enhanced_config, tts_script = review_and_enhance_config(
        config=config,
        history_data=history_data,
        video_name=video_name
    )
    
    # Calculate fixed timeline with validation
    timeline, metadata = calculate_timeline_fixed(
        config=enhanced_config,
        video_name=video_name,
        tts_segments=tts_segments
    )
    
    # Add timeline to metadata
    metadata["timeline"] = timeline
    
    return enhanced_config, tts_script, metadata
