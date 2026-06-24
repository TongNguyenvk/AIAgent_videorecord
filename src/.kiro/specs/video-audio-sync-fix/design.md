# Video-Audio Sync Fix Bugfix Design

## Overview

This bugfix addresses critical synchronization issues in the Webreel pipeline where narration audio and video actions become misaligned, causing audio overlaps, premature video termination, and actions executing at incorrect times. The root cause is a fundamental mismatch between three separate timeline calculations: (1) AI reviewer's estimates in `calculate_timeline()`, (2) audio sync optimizer's `accumulated_time_ms` tracking in `inject_audio_pauses()`, and (3) the actual video recording timeline from webreel with page load waits. The fix will unify these timeline calculations by making the AI reviewer's timeline the single source of truth, validating it against actual TTS durations, and ensuring the pause injection logic accounts for reordering and page load waits.

## Glossary

- **Bug_Condition (C)**: The condition that triggers synchronization bugs - when the pipeline processes multi-segment narration videos where timeline calculations diverge
- **Property (P)**: The desired behavior - narration audio and video actions remain synchronized throughout the entire video with no overlaps or premature termination
- **Preservation**: Existing single-action video generation, TTS audio generation, webreel recording, and MoviePy composition that work correctly
- **calculate_timeline()**: The function in `ai_reviewer.py` that estimates step durations and generates timeline data (currently uses rough estimates)
- **inject_audio_pauses()**: The function in `audio_sync_optimizer.py` that inserts narration pauses before actions and calculates `start_time` for audio overlay (currently has misaligned timeline tracking)
- **accumulated_time_ms**: The timeline tracker in `inject_audio_pauses()` that calculates when each audio segment should start (currently doesn't match actual video timeline)
- **start_time**: The timestamp assigned to each audio segment for MoviePy overlay (currently calculated incorrectly)
- **meaningful steps**: Non-pause actions that have corresponding narration segments (navigate, click, type, etc.)
- **page_load_wait_ms**: The 3000ms wait added after navigate/click actions for DOM to settle (currently not accounted for in timeline calculation)
- **TTS duration**: The actual measured audio duration from FPT.AI TTS using mutagen (currently not validated against AI reviewer estimates)

## Bug Details

### Bug Condition

The bug manifests when the pipeline processes a video with multiple narration segments where three separate timeline calculations diverge: (1) the AI reviewer estimates step durations without accounting for page load waits or pause injection reordering, (2) the audio sync optimizer tracks `accumulated_time_ms` but doesn't properly account for page load waits that occur AFTER actions, and (3) the actual webreel recording includes page load waits that shift the entire timeline. This causes narration `start_time` values to be calculated incorrectly, leading to audio overlaps, delayed actions, and premature video termination.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type PipelineExecution
  OUTPUT: boolean
  
  RETURN input.narration_segments.length > 1
         AND calculate_timeline_estimates != actual_tts_durations
         AND accumulated_time_ms != actual_video_timeline
         AND page_load_waits NOT accounted_for_in_timeline
         AND pause_injection_reordering NOT reflected_in_start_time
END FUNCTION
```

### Examples

- **Example 1 (Initial delay)**: In w3test case, segment 1 narration finishes at ~2432ms but the first action waits until 2000ms + additional time, creating dead air where nothing happens
- **Example 2 (Audio overlap)**: Segment 1 audio at start_time=0 overlaps with segment 2 audio at start_time=2.432 because the actual video timeline has shifted due to page load waits not being accounted for
- **Example 3 (Delayed action)**: Segment 2 says "click Python" but the click action is delayed significantly because `accumulated_time_ms` calculation doesn't match the actual video timeline after the navigate action's 3000ms page load wait
- **Example 4 (Premature termination)**: Segment 3 says "press start learning" but the video ends before the action executes because the timeline calculation underestimated the total video duration
- **Edge case (Single segment)**: A video with only one narration segment works correctly because there are no cumulative timing errors from multiple segments

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- Single-action videos with one narration segment must continue to generate synchronized output correctly
- FPT.AI TTS audio generation with mutagen duration measurement must continue to work
- Webreel video recording with Chrome CDP and cursor animation must continue to capture all actions
- MoviePy audio overlay mechanism must continue to work (only the timing calculation changes)
- The design pattern of injecting narration pauses BEFORE actions must be preserved
- Vietnamese narration generation must continue to work correctly
- AI reviewer's intelligent narration content generation must continue to work

**Scope:**
All inputs that do NOT involve multi-segment narration videos should be completely unaffected by this fix. This includes:
- Simple single-action tasks with one narration segment
- Videos where the welcome segment is the only narration
- Any existing functionality in TTS generation, webreel recording, or MoviePy composition that doesn't depend on timeline calculation

## Hypothesized Root Cause

Based on the bug description and code analysis, the root causes are:

1. **Timeline Calculation Mismatch**: The AI reviewer's `calculate_timeline()` uses rough estimates (navigate=2s, click=0.5s) that don't match actual TTS durations (e.g., estimated 4-8s vs actual 2432ms). These estimates are never validated against the measured audio durations from FPT.AI TTS.

2. **Page Load Wait Omission**: The `calculate_timeline()` function doesn't account for the 3000ms page load waits that are added after navigate/click actions in the actual video recording. This causes cumulative timing drift where each page load action shifts the timeline by 3000ms.

3. **Pause Injection Reordering Not Reflected**: The `inject_audio_pauses()` function inserts narration pauses BEFORE actions, but the `accumulated_time_ms` calculation treats them as if they occur in the original order. When calculating `seg.start_time`, it doesn't account for the fact that the pause has been moved before the action.

4. **Accumulated Time Calculation Error**: The `accumulated_time_ms` tracking in `inject_audio_pauses()` calculates action durations (navigate=page_load_wait_ms, click=500ms) but adds page load waits at the wrong point in the timeline. Page load waits occur AFTER the action completes, but the calculation adds them immediately.

5. **No Timeline Validation**: There is no validation step that compares the AI reviewer's timeline estimates against the actual measured TTS durations or the actual video recording timeline. This allows divergence to accumulate undetected.

## Correctness Properties

Property 1: Bug Condition - Timeline Synchronization

_For any_ pipeline execution where multiple narration segments are generated, the fixed system SHALL ensure that (1) AI reviewer timeline estimates are validated against actual TTS durations, (2) pause injection logic accounts for reordering and page load waits, (3) `start_time` values accurately reflect the actual video timeline, and (4) all narration segments play without overlap and all actions execute before video termination.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10**

Property 2: Preservation - Single-Segment and Existing Functionality

_For any_ pipeline execution that does NOT involve multi-segment narration videos (single-action tasks, single narration segment), the fixed system SHALL produce exactly the same behavior as the original system, preserving all existing functionality for TTS generation, webreel recording, MoviePy composition, and the narration-before-action design pattern.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `webreel-ai-agent/src/ai_reviewer.py`

**Function**: `calculate_timeline()`

**Specific Changes**:
1. **Add Page Load Wait Accounting**: Include `page_load_wait_ms` (3000ms) in duration calculation for navigate and click actions
   - Change navigate duration from 2.0s to 2.0s + 3.0s = 5.0s
   - Change click duration from 0.5s to 0.5s + 3.0s = 3.5s (if click triggers page load)
   
2. **Add Timeline Validation Hook**: Add a parameter to accept actual TTS durations for validation
   - Add optional parameter `tts_segments: list[AudioSegment] | None = None`
   - If provided, compare estimated narration durations against actual TTS durations
   - Log warnings if divergence exceeds threshold (e.g., >20% difference)

3. **Return Enhanced Timeline**: Include metadata for downstream validation
   - Add `total_duration` field to return value
   - Add `narration_points` list indicating where narration segments should be inserted

**File**: `webreel-ai-agent/src/audio_sync_optimizer.py`

**Function**: `inject_audio_pauses()`

**Specific Changes**:
1. **Fix Accumulated Time Calculation**: Correctly account for pause injection reordering
   - When injecting a narration pause BEFORE an action, set `seg.start_time = accumulated_time_ms / 1000.0` BEFORE adding the pause duration
   - Add the narration pause duration to `accumulated_time_ms` BEFORE processing the action
   - This ensures `start_time` reflects when the audio should start in the actual video timeline

2. **Fix Page Load Wait Timing**: Add page load waits AFTER action duration, not during
   - For navigate actions: add action duration (0ms for navigate itself) + page_load_wait_ms (3000ms)
   - For click actions: add click animation (500ms) + defaultDelay + page_load_wait_ms (3000ms) only if click triggers page load
   - Remove the current incorrect handling where page_load_wait_ms is added immediately for navigate

3. **Add Timeline Validation**: Compare calculated timeline against AI reviewer estimates
   - Accept AI reviewer timeline as parameter: `ai_timeline: list[dict] | None = None`
   - After building new_steps, calculate total duration and compare against AI timeline
   - Log warnings if divergence exceeds threshold

4. **Improve Segment Mapping**: Use AI reviewer's narration_points instead of sequential mapping
   - Replace the current sequential mapping (`step_to_segment`) with mapping based on AI reviewer's intended timeline
   - This ensures narration segments align with the actions they describe

**File**: `webreel-ai-agent/run_pipeline_unified_chrome.py`

**Function**: `audio_sync_phase()` and `ai_review_config()`

**Specific Changes**:
1. **Pass Timeline Between Phases**: Connect AI reviewer timeline to audio sync optimizer
   - In `ai_review_config()`, return the timeline from `calculate_timeline()` along with tts_script
   - In `audio_sync_phase()`, accept the AI timeline and pass it to `inject_audio_pauses()`
   - After TTS generation, pass actual audio segments back to `calculate_timeline()` for validation

2. **Add Validation Logging**: Log timeline comparisons for debugging
   - Log AI reviewer estimated total duration
   - Log audio sync optimizer calculated total duration
   - Log any divergence warnings

3. **Add Timeline Checkpoint**: Save timeline data for debugging
   - Save AI reviewer timeline to `{output_dir}/ai_timeline.json`
   - Save audio sync timeline to `{output_dir}/audio_sync_timeline.json`
   - This enables post-mortem analysis of timing issues

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the synchronization bugs on unfixed code using the w3test case, then verify the fix works correctly across multiple scenarios and preserves existing single-segment functionality.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate the synchronization bugs BEFORE implementing the fix. Confirm or refute the root cause analysis. If we refute, we will need to re-hypothesize.

**Test Plan**: Run the w3test case (Wikipedia search with 3 narration segments) on the UNFIXED code and measure actual timings at each phase. Compare AI reviewer estimates, audio sync calculations, and actual video timeline to identify divergence points.

**Test Cases**:
1. **Timeline Estimate Test**: Run AI reviewer on w3test config and log estimated durations (will show navigate=2s, click=0.5s estimates)
2. **TTS Duration Test**: Generate TTS audio for w3test and measure actual durations with mutagen (will show actual ~2432ms vs estimates)
3. **Accumulated Time Test**: Add logging to `inject_audio_pauses()` to track `accumulated_time_ms` and `seg.start_time` values (will show incorrect timeline)
4. **Video Recording Test**: Record w3test video and manually measure when actions occur in the video (will show 3000ms page load waits not accounted for)
5. **Audio Overlay Test**: Compose final video and observe audio overlaps and timing mismatches (will demonstrate the bug)

**Expected Counterexamples**:
- AI reviewer estimates 4-8s for narration segments but actual TTS is ~2.4s
- `accumulated_time_ms` calculation shows segment 2 starting at ~2.4s but actual video has it at ~5.4s due to page load wait
- Audio overlaps occur at segment transitions in final composed video
- Video terminates before segment 3 action executes

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds (multi-segment narration videos), the fixed system produces synchronized output with no overlaps or premature termination.

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := run_pipeline_fixed(input)
  ASSERT no_audio_overlaps(result)
  ASSERT all_actions_execute_before_termination(result)
  ASSERT narration_action_timing_aligned(result)
END FOR
```

**Test Cases**:
1. **W3test Case**: Run the fixed pipeline on w3test and verify all 3 segments play without overlap and all actions execute
2. **Multi-Segment Stress Test**: Create a test case with 5+ narration segments and verify synchronization throughout
3. **Page Load Heavy Test**: Create a test case with multiple navigate/click actions that trigger page loads and verify timing
4. **Mixed Action Test**: Create a test case with navigate, click, type, scroll actions and verify all are synchronized

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold (single-segment videos, simple tasks), the fixed system produces the same result as the original system.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT run_pipeline_original(input) = run_pipeline_fixed(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-buggy inputs

**Test Plan**: Run both unfixed and fixed pipelines on single-segment test cases and compare outputs byte-for-byte (or with tolerance for timestamp variations).

**Test Cases**:
1. **Single Action Preservation**: Run a simple "navigate to google.com" task with one narration segment on both versions
2. **Welcome Segment Only**: Run a task where only the welcome segment has narration and verify identical output
3. **No Narration Preservation**: Run a task with no narration segments and verify webreel recording is unchanged
4. **TTS Generation Preservation**: Verify FPT.AI TTS generates identical audio files for the same input text

### Unit Tests

- Test `calculate_timeline()` with page load wait accounting (verify navigate=5s, click=3.5s durations)
- Test `calculate_timeline()` validation against actual TTS durations (verify warnings when divergence >20%)
- Test `inject_audio_pauses()` accumulated time calculation with reordering (verify `start_time` values)
- Test `inject_audio_pauses()` page load wait timing (verify waits added after actions)
- Test segment mapping logic with AI timeline narration_points
- Test edge cases: empty segments list, single segment, no meaningful steps

### Property-Based Tests

- Generate random multi-segment narration videos and verify no audio overlaps in composed output
- Generate random action sequences and verify timeline calculations are consistent across all phases
- Generate random TTS durations and verify timeline validation catches divergence
- Test that all single-segment videos produce identical output before and after fix

### Integration Tests

- Run full w3test pipeline and verify synchronization at each phase (AI review → TTS → audio sync → record → compose)
- Run multiple test cases with varying segment counts (2, 3, 5, 10 segments) and verify all work correctly
- Test pipeline with different page load wait configurations (1000ms, 3000ms, 5000ms)
- Test pipeline with Vietnamese and English narration to verify language independence
- Manually review composed videos to verify visual and audio synchronization quality
