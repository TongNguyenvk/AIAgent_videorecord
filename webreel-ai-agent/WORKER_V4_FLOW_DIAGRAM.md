# OS Worker V4 - Flow Diagram

Visual representation of the updated OS Worker flow with V4 pipeline support.

## Complete Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER SUBMITS JOB                        │
│                                                                 │
│  Frontend → Backend API → Redis Queue (os-queue)                │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      OS WORKER (Windows)                        │
│                                                                 │
│  1. Poll Redis Queue (every 10s)                                │
│  2. Check user idle (>2 minutes)                                │
│  3. Pick up job                                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    DETECT PIPELINE VERSION                      │
│                                                                 │
│  if config.get("app_type"):                                     │
│      → V4 Pipeline (auto-launch)                                │
│  else:                                                          │
│      → V3 Pipeline (legacy)                                     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
                    ┌─────────┴─────────┐
                    │                   │
                   V4                  V3
                    │                   │
                    ↓                   ↓
    ┌───────────────────────┐   ┌──────────────────┐
    │   V4 PIPELINE FLOW    │   │  V3 PIPELINE     │
    │   (Automated)         │   │  (Legacy)        │
    └───────────────────────┘   └──────────────────┘
                    │                   │
                    ↓                   ↓
    ┌───────────────────────┐   ┌──────────────────┐
    │ PHASE 0: FILE DOWNLOAD│   │ PHASE 1: PLANNING│
    │                       │   │ (Manual launch)  │
    │ • Download from URL   │   └──────────────────┘
    │ • Save to local path  │            ↓
    │ • Progress tracking   │   ┌──────────────────┐
    │ • Error handling      │   │ PHASE 2: TTS     │
    └───────────────────────┘   └──────────────────┘
                    ↓                   ↓
    ┌───────────────────────┐   ┌──────────────────┐
    │ PHASE 0: APP LAUNCH   │   │ PHASE 3: RECORD  │
    │                       │   │ (Manual reset)   │
    │ • Launch app          │   └──────────────────┘
    │ • Open file           │            ↓
    │ • Get PID             │   ┌──────────────────┐
    └───────────────────────┘   │ PHASE 4: MIX     │
                    ↓           └──────────────────┘
    ┌───────────────────────┐            ↓
    │ PHASE 1: PLANNING     │   ┌──────────────────┐
    │                       │   │ PHASE 5: RENDER  │
    │ • Agent explores      │   └──────────────────┘
    │ • Generate plan.json  │            │
    │ • Generate narrations │            │
    └───────────────────────┘            │
                    ↓                    │
    ┌───────────────────────┐            │
    │ PHASE 2: TTS          │            │
    │                       │            │
    │ • Generate audio      │            │
    │ • Save to audio/      │            │
    └───────────────────────┘            │
                    ↓                    │
    ┌───────────────────────┐            │
    │ PHASE 2.75: RESET     │            │
    │                       │            │
    │ • Close app           │            │
    │ • Restore from backup │            │
    │ • Reopen app          │            │
    └───────────────────────┘            │
                    ↓                    │
    ┌───────────────────────┐            │
    │ PHASE 3: RECORDING    │            │
    │                       │            │
    │ • Replay plan.json    │            │
    │ • Capture video       │            │
    │ • Take screenshots    │            │
    └───────────────────────┘            │
                    ↓                    │
    ┌───────────────────────┐            │
    │ PHASE 4: AUDIO MIX    │            │
    │                       │            │
    │ • Mix narrations      │            │
    │ • Sync with video     │            │
    └───────────────────────┘            │
                    ↓                    │
    ┌───────────────────────┐            │
    │ PHASE 5: RENDER       │            │
    │                       │            │
    │ • Generate DOCX       │            │
    │ • Generate PDF        │            │
    └───────────────────────┘            │
                    │                    │
                    └────────┬───────────┘
                             ↓
            ┌────────────────────────────┐
            │      UPLOAD RESULTS        │
            │                            │
            │ • Video (MP4)              │
            │ • Document (DOCX)          │
            │ • PDF                      │
            │                            │
            │ → VPS (R2/Local Storage)   │
            └────────────────────────────┘
                             ↓
            ┌────────────────────────────┐
            │    CLEANUP (V4 only)       │
            │                            │
            │ • Delete downloaded files  │
            │ • Delete backup files      │
            │ • Free disk space          │
            └────────────────────────────┘
                             ↓
            ┌────────────────────────────┐
            │      RETURN RESULT         │
            │                            │
            │ {                          │
            │   "status": "completed",   │
            │   "video_path": "...",     │
            │   "uploaded": true         │
            │ }                          │
            └────────────────────────────┘
```

## V4 vs V3 Comparison

```
┌─────────────────────────────────────────────────────────────────┐
│                         V4 PIPELINE                             │
│                         (Automated)                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Job Config:                                                    │
│  {                                                              │
│    "app_type": "excel",                                         │
│    "uploaded_file_url": "https://..."                           │
│  }                                                              │
│                                                                 │
│  Worker Actions:                                                │
│  ✅ Download file automatically                                 │
│  ✅ Launch app automatically                                    │
│  ✅ Reset state automatically                                   │
│  ✅ Cleanup files automatically                                 │
│                                                                 │
│  User Actions:                                                  │
│  ❌ None required!                                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         V3 PIPELINE                             │
│                         (Legacy)                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Job Config:                                                    │
│  {                                                              │
│    "target_pid": 12345                                          │
│  }                                                              │
│                                                                 │
│  Worker Actions:                                                │
│  ❌ No file download                                            │
│  ❌ No app launch                                               │
│  ❌ No state reset                                              │
│  ❌ No cleanup                                                  │
│                                                                 │
│  User Actions:                                                  │
│  ✅ Manually open app                                           │
│  ✅ Manually open file                                          │
│  ✅ Manually reset state (Ctrl+Z)                               │
│  ✅ Manually cleanup files                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## File Locations

```
┌─────────────────────────────────────────────────────────────────┐
│                      FILE SYSTEM LAYOUT                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  C:\webreel_uploads\                                            │
│    └─ {job_id}\                                                 │
│        └─ {filename}  ← Downloaded file                         │
│                                                                 │
│  C:\webreel_backups\                                            │
│    └─ {filename}_{timestamp}.{ext}  ← Backup for reset         │
│                                                                 │
│  os_recorder/workspace/output/                                  │
│    └─ {video_name}/                                             │
│        ├─ agent/                                                │
│        │   ├─ plan.json                                         │
│        │   └─ narrations.json                                   │
│        ├─ audio/                                                │
│        │   ├─ narration_0.mp3                                   │
│        │   └─ narration_1.mp3                                   │
│        ├─ screenshots/                                          │
│        │   ├─ step_0.png                                        │
│        │   └─ step_1.png                                        │
│        ├─ {video_name}_raw.mp4                                  │
│        ├─ {video_name}_final.mp4  ← Uploaded                    │
│        ├─ {video_name}_document.docx  ← Uploaded                │
│        └─ {video_name}_document.pdf  ← Uploaded                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## State Transitions

```
┌─────────────────────────────────────────────────────────────────┐
│                      WORKER STATE MACHINE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  IDLE                                                           │
│    ↓                                                            │
│  POLLING (check queue every 10s)                                │
│    ↓                                                            │
│  JOB_RECEIVED                                                   │
│    ↓                                                            │
│  DOWNLOADING (V4 only)                                          │
│    ↓                                                            │
│  PROCESSING                                                     │
│    ├─ Phase 0: App Launch (V4 only)                            │
│    ├─ Phase 1: Planning                                        │
│    ├─ Phase 2: TTS                                             │
│    ├─ Phase 2.75: Reset (V4 only)                              │
│    ├─ Phase 3: Recording                                       │
│    ├─ Phase 4: Mixing                                          │
│    └─ Phase 5: Rendering                                       │
│    ↓                                                            │
│  UPLOADING                                                      │
│    ↓                                                            │
│  CLEANING_UP (V4 only)                                          │
│    ↓                                                            │
│  COMPLETED                                                      │
│    ↓                                                            │
│  IDLE (back to polling)                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Error Handling Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      ERROR HANDLING                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Download Error                                                 │
│    ↓                                                            │
│  Log error                                                      │
│    ↓                                                            │
│  Return failed status                                           │
│    ↓                                                            │
│  Job marked as failed                                           │
│    ↓                                                            │
│  No upload, no cleanup                                          │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  Pipeline Error                                                 │
│    ↓                                                            │
│  Log error                                                      │
│    ↓                                                            │
│  Return failed status                                           │
│    ↓                                                            │
│  Job marked as failed                                           │
│    ↓                                                            │
│  No upload, no cleanup                                          │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  Upload Error                                                   │
│    ↓                                                            │
│  Log error                                                      │
│    ↓                                                            │
│  Return completed status (with uploaded=false)                  │
│    ↓                                                            │
│  No cleanup (files preserved for retry)                         │
│                                                                 │
│  ─────────────────────────────────────────────────────────────  │
│                                                                 │
│  Cleanup Error (Non-Fatal)                                      │
│    ↓                                                            │
│  Log warning                                                    │
│    ↓                                                            │
│  Return completed status (with uploaded=true)                   │
│    ↓                                                            │
│  Job still marked as successful                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Timeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    TYPICAL JOB TIMELINE                         │
│                    (Excel Pivot Table)                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  00:00 - Job submitted to queue                                 │
│  00:01 - Worker picks up job                                    │
│  00:02 - File download starts (2.5 MB)                          │
│  00:12 - File download complete (10s)                           │
│  00:13 - Excel launches with file                               │
│  00:17 - Phase 1: Agent planning (15 steps)                     │
│  01:47 - Phase 1 complete (90s)                                 │
│  01:48 - Phase 2: TTS generation (8 narrations)                 │
│  02:18 - Phase 2 complete (30s)                                 │
│  02:19 - Phase 2.75: State reset (close + reopen)               │
│  02:23 - Phase 2.75 complete (4s)                               │
│  02:24 - Phase 3: Recording (8 actions)                         │
│  03:04 - Phase 3 complete (40s)                                 │
│  03:05 - Phase 4: Audio mixing                                  │
│  03:15 - Phase 4 complete (10s)                                 │
│  03:16 - Phase 5: Document rendering                            │
│  03:26 - Phase 5 complete (10s)                                 │
│  03:27 - Upload starts (3 files, 15 MB total)                   │
│  03:42 - Upload complete (15s)                                  │
│  03:43 - Cleanup starts                                         │
│  03:44 - Cleanup complete (1s)                                  │
│  03:45 - Job marked as completed                                │
│                                                                 │
│  Total: ~3 minutes 45 seconds                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Legend

```
✅ = Automated (no user action)
❌ = Not available / Manual required
→ = Data flow
↓ = Process flow
├─ = Branch
└─ = End of branch
```
