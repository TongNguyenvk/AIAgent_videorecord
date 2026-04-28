# Bugfix Requirements Document

## Introduction

This document addresses critical video-audio synchronization issues in the Webreel pipeline that cause narration and action timing mismatches, audio overlaps, and premature video termination. The bug manifests in the 5-phase pipeline (browser-use agent → webreel config conversion → AI review → TTS audio sync → webreel record → MoviePy compose) where timeline calculations, pause injection logic, and segment mapping fail to maintain proper synchronization between generated narration audio and recorded video actions.

The primary impact is unusable output videos where:
- Initial segments have excessive delays before actions begin
- Narration segments overlap at transition points
- Actions execute at incorrect times relative to their narration
- Videos terminate before completing all intended actions

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN the pipeline generates a video with multiple narration segments THEN the initial segment waits 2000ms before starting while the narration has already finished playing

1.2 WHEN transitioning between narration segments (e.g., segment 1 to segment 2) THEN the audio from consecutive segments overlaps causing unintelligible narration

1.3 WHEN the AI reviewer's `calculate_timeline()` estimates segment durations THEN these estimates do not match the actual measured audio durations from FPT.AI TTS (e.g., estimated 4-8s vs actual 2432ms)

1.4 WHEN `inject_audio_pauses()` maps narration segments to "meaningful steps" sequentially THEN the mapping does not align with the AI reviewer's intended timeline causing actions to execute at wrong times

1.5 WHEN `inject_audio_pauses()` calculates `start_time` based on `accumulated_time_ms` THEN this calculated time does not match the actual video recording timeline from webreel

1.6 WHEN MoviePy composes the final video using `seg.start_time` for audio overlay THEN the overlay timing does not match the actual action timing in the recorded video

1.7 WHEN the video reaches segment 2 in the w3test case THEN the action (clicking Python link) is delayed significantly compared to the narration saying "click Python"

1.8 WHEN the narration says "press start learning" THEN the video ends before the corresponding action executes

1.9 WHEN page load waits (3000ms) are added after navigate/click actions THEN these waits are not accounted for in the timeline calculation causing cumulative timing drift

1.10 WHEN narration pauses are injected BEFORE actions in the config THEN the timeline calculation does not account for this reordering causing misalignment between planned and actual execution

### Expected Behavior (Correct)

2.1 WHEN the pipeline generates a video with multiple narration segments THEN the initial pause SHALL be minimal (500-1000ms) and actions SHALL begin immediately after the first narration finishes

2.2 WHEN transitioning between narration segments THEN there SHALL be no audio overlap and each segment SHALL play completely before the next begins

2.3 WHEN the AI reviewer's `calculate_timeline()` estimates segment durations THEN these estimates SHALL match or be validated against actual measured audio durations from TTS generation

2.4 WHEN `inject_audio_pauses()` maps narration segments to actions THEN the mapping SHALL align with the AI reviewer's intended timeline and preserve the semantic relationship between narration and action

2.5 WHEN `inject_audio_pauses()` calculates `start_time` THEN this time SHALL accurately reflect the actual video timeline including all page load waits, action durations, and previously injected pauses

2.6 WHEN MoviePy composes the final video THEN the audio overlay timing SHALL synchronize with the actual action timing in the recorded video

2.7 WHEN the video reaches segment 2 in the w3test case THEN the action (clicking Python link) SHALL execute immediately after the narration "click Python" finishes

2.8 WHEN the narration says "press start learning" THEN the corresponding action SHALL execute before the video ends

2.9 WHEN page load waits are added after navigate/click actions THEN these waits SHALL be included in the timeline calculation to prevent cumulative timing drift

2.10 WHEN narration pauses are injected BEFORE actions THEN the timeline calculation SHALL account for this reordering to maintain alignment between planned and actual execution

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the pipeline processes a simple single-action task THEN the system SHALL CONTINUE TO generate synchronized video-audio output correctly

3.2 WHEN the welcome segment (segment 1) plays in the w3test case THEN the system SHALL CONTINUE TO maintain proper synchronization as it currently does

3.3 WHEN FPT.AI TTS generates audio files THEN the system SHALL CONTINUE TO use mutagen for accurate duration measurement

3.4 WHEN the AI reviewer generates TTS scripts with timeline estimates THEN the system SHALL CONTINUE TO provide intelligent narration content

3.5 WHEN webreel records video with cursor animation via CDP THEN the system SHALL CONTINUE TO capture all actions correctly

3.6 WHEN the pipeline uses Chrome CDP for unified browser control THEN the system SHALL CONTINUE TO execute actions reliably

3.7 WHEN narration pauses are injected before actions THEN the system SHALL CONTINUE TO use this design pattern (the pattern itself is correct, only the timing calculation needs fixing)

3.8 WHEN the pipeline processes Vietnamese narration THEN the system SHALL CONTINUE TO generate correct TTS audio via FPT.AI

3.9 WHEN MoviePy composes the final video THEN the system SHALL CONTINUE TO overlay audio onto video (the overlay mechanism is correct, only the timing needs fixing)

3.10 WHEN the pipeline generates the webreel config JSON THEN the system SHALL CONTINUE TO include all necessary action metadata and pause information
