# Pipeline Modules Analysis - Tổng hợp cấu trúc và dependencies

## Tổng quan

Dự án hiện có 4 pipeline chính:
1. **Web Worker** (Docker Linux) - Web tutorial recording
2. **Office Worker** (Docker Linux) - Slide-to-Video
3. **OS Worker** (Windows native) - OS automation recording
4. **Desktop App** (Windows Flet GUI) - Local web recording

## 1. Web Worker Pipeline

### Entry Point
- `worker/web_worker.py` → `desktop_app/pipeline.py` → `run_pipeline_v3()`

### Core Dependencies
```
worker/web_worker.py
├── backend/queue.py (Redis queue)
├── desktop_app/pipeline.py (main pipeline)
│   ├── desktop_app/bu_to_webreel.py (parser)
│   ├── desktop_app/audio_injector.py (TTS Phase 3)
│   │   ├── desktop_app/tts.py (FPT TTS)
│   │   └── desktop_app/tts_edge.py (Edge TTS) ⚠️ KHÔNG có retry
│   ├── desktop_app/trace_composer.py (Phase 6)
│   ├── desktop_app/webreel_runner.py (Webreel CLI wrapper)
│   └── desktop_app/browser-use/ (Phase 1 agent)
└── Chrome management (launch/kill)
```

### Modules Dùng
- `desktop_app/pipeline.py` - Main orchestrator
- `desktop_app/bu_to_webreel.py` - History → Config parser
- `desktop_app/audio_injector.py` - TTS generation (concurrent với Semaphore)
- `desktop_app/tts_edge.py` - Edge TTS wrapper ⚠️ KHÔNG có retry logic
- `desktop_app/tts.py` - FPT TTS wrapper
- `desktop_app/trace_composer.py` - Audio sync composer
- `desktop_app/webreel_runner.py` - Webreel CLI runner
- `desktop_app/browser-use/` - Browser automation agent

### Vấn đề hiện tại
- ❌ `desktop_app/tts_edge.py` KHÔNG có retry logic → gây lỗi "No audio received" trong Docker
- ❌ Import từ local `desktop_app/` thay vì `shared/`
- ❌ Concurrent TTS dùng Semaphore phức tạp, khác với OS recorder

---

## 2. Office Worker Pipeline

### Entry Point
- `worker/office_worker.py` → `desktop_app/slide_pipeline/` (chưa hoàn chỉnh)

### Core Dependencies
```
worker/office_worker.py
├── backend/queue.py
└── desktop_app/slide_pipeline/
    ├── extractor.py (PPTX → images)
    ├── narration_generator.py (AI narration)
    └── video_composer.py (ffmpeg)
```

### Modules Dùng
- `desktop_app/slide_pipeline/extractor.py` - Extract slides từ PPTX/PDF
- `desktop_app/slide_pipeline/narration_generator.py` - AI tạo narration
- `desktop_app/slide_pipeline/video_composer.py` - Ghép video từ slides
- Có thể dùng `shared/tts_edge.py` cho TTS

### Trạng thái
- ⚠️ Pipeline chưa hoàn chỉnh, cần tích hợp TTS và composer

---

## 3. OS Worker Pipeline

### Entry Point
- `worker/os_worker.py` → `os_recorder/os_pipeline_main.py` → `run_os_pipeline_v3_dual()`

### Core Dependencies
```
worker/os_worker.py
├── backend/queue.py
└── os_recorder/os_pipeline_main.py
    ├── os_recorder/core/os_planning_agent_v2.py (Phase 1)
    ├── os_recorder/core/tts_edge.py (Phase 2) ✅ Đơn giản, ổn định
    ├── os_recorder/core/media_engine.py (TTS + FFmpeg)
    ├── os_recorder/core/sync_recorder.py (Phase 3)
    ├── os_recorder/core/trace_composer.py (Phase 4)
    └── dual_output_pipeline/ (Phase 5 - DOCX/PDF)
```

### Modules Dùng
- `os_recorder/core/os_planning_agent_v2.py` - Agent dò đường (Gemini Vision)
- `os_recorder/core/tts_edge.py` - Edge TTS ✅ Đơn giản, không retry nhưng ổn định
- `os_recorder/core/media_engine.py` - TTS + FFmpeg recording
  - `generate_audio()` - Wrapper đơn giản cho Edge TTS
  - `start_screen_recording()` - FFmpeg gdigrab
- `os_recorder/core/sync_recorder.py` - Replay plan + record
- `os_recorder/core/trace_composer.py` - Audio sync (tương tự desktop_app)
- `os_recorder/core/ui_inspector.py` - UI Automation element detection
- `os_recorder/core/window_manager.py` - Window management
- `os_recorder/core/excel_engine.py` - Excel COM automation
- `dual_output_pipeline/` - Document rendering

### Đặc điểm
- ✅ TTS đơn giản, gọi trực tiếp `edge_tts.Communicate()` trong `media_engine.py`
- ✅ Concurrent TTS dùng `asyncio.gather()` đơn giản trong `media_engine.py`
- ✅ Không dùng ThreadPoolExecutor hay Semaphore phức tạp
- ✅ Ổn định hơn web worker

---

## 4. Desktop App (Flet GUI)

### Entry Point
- `desktop_app/app_flet.py` → `desktop_app/pipeline.py` → `run_pipeline_v3()`

### Core Dependencies
```
desktop_app/app_flet.py
└── desktop_app/pipeline.py (giống web_worker)
    ├── desktop_app/bu_to_webreel.py
    ├── desktop_app/audio_injector.py
    ├── desktop_app/tts_edge.py ⚠️
    ├── desktop_app/trace_composer.py
    └── desktop_app/webreel_runner.py
```

### Modules Dùng
- Giống hệt Web Worker
- Thêm `desktop_app/app_flet.py` - Flet GUI
- Thêm `desktop_app/browser_launcher.py` - Chrome launcher cho Windows

---

## 5. Shared Modules (Canonical)

### Mục đích
Theo `phase1_product.md`, `shared/` là nơi chứa các module canonical dùng chung giữa các pipeline.

### Modules hiện có
```
shared/
├── __init__.py
├── tts.py ✅ FPT TTS với retry logic
├── tts_edge.py ✅ Edge TTS với retry logic (vừa thêm)
├── audio_injector.py ⚠️ Chưa được dùng
├── bu_to_webreel.py ⚠️ Chưa được dùng
├── trace_composer.py ⚠️ Chưa được dùng
└── webreel_runner.py ⚠️ Chưa được dùng
```

### Trạng thái
- ✅ `shared/tts_edge.py` đã có retry logic (vừa thêm)
- ❌ Các module khác chưa được import/sử dụng bởi bất kỳ pipeline nào
- ❌ Desktop app và web worker vẫn import từ `desktop_app/` local

---

## 6. Modules Trùng lặp

### TTS Modules (5 bản copy)
| File | Retry Logic | Concurrent | Được dùng bởi |
|------|-------------|------------|---------------|
| `shared/tts_edge.py` | ✅ Có (mới thêm) | Semaphore | ❌ Không ai dùng |
| `desktop_app/tts_edge.py` | ✅ Có (mới thêm) | Semaphore | ✅ Web worker, Desktop app |
| `desktop_app/v3/tts_edge.py` | ✅ Có | Semaphore | ❌ Không ai dùng |
| `os_recorder/core/tts_edge.py` | ❌ Không | ❌ Không | ✅ OS worker (qua media_engine) |
| `src/tts_edge.py` | ❌ Không | ❌ Không | ❌ Legacy |
| `v3/tts_edge.py` | ✅ Có | ❌ Không | ❌ Legacy |

### Audio Injector (5 bản copy)
| File | Concurrent Mode | Được dùng bởi |
|------|-----------------|---------------|
| `shared/audio_injector.py` | Semaphore (MAX_CONCURRENT=3) | ❌ Không ai dùng |
| `desktop_app/audio_injector.py` | Semaphore (MAX_CONCURRENT=3) | ✅ Web worker, Desktop app |
| `desktop_app/v3/audio_injector.py` | `asyncio.gather()` parallel | ❌ Không ai dùng |
| `os_recorder/core/media_engine.py` | `asyncio.gather()` parallel | ✅ OS worker |
| `src/audio_injector.py` | Semaphore | ❌ Legacy |
| `v3/audio_injector.py` | ❌ Không | ❌ Legacy |

### Bu to Webreel Parser (4 bản copy)
| File | Được dùng bởi |
|------|---------------|
| `shared/bu_to_webreel.py` | ❌ Không ai dùng |
| `desktop_app/bu_to_webreel.py` | ✅ Web worker, Desktop app |
| `src/bu_to_webreel.py` | ❌ Legacy |
| `v3/bu_to_webreel_v3.py` | ❌ Legacy |

### Trace Composer (4 bản copy)
| File | Được dùng bởi |
|------|---------------|
| `shared/trace_composer.py` | ❌ Không ai dùng |
| `desktop_app/trace_composer.py` | ✅ Web worker, Desktop app |
| `os_recorder/core/trace_composer.py` | ✅ OS worker |
| `src/trace_composer.py` | ❌ Legacy |

### Webreel Runner (3 bản copy)
| File | Được dùng bởi |
|------|---------------|
| `shared/webreel_runner.py` | ❌ Không ai dùng |
| `desktop_app/webreel_runner.py` | ✅ Web worker, Desktop app |
| `src/webreel_runner.py` | ❌ Legacy |

### TTS FPT (3 bản copy)
| File | Retry Logic | Được dùng bởi |
|------|-------------|---------------|
| `shared/tts.py` | ✅ Có | ❌ Không ai dùng |
| `desktop_app/tts.py` | ✅ Có | ✅ Web worker, Desktop app |
| `os_recorder/core/tts.py` | ✅ Có | ✅ OS worker |
| `src/tts.py` | ✅ Có | ❌ Legacy |

---

## 7. So sánh TTS Implementation

### OS Recorder (Ổn định)
```python
# os_recorder/core/media_engine.py
async def _generate_audio_async(text, output_path, voice):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)
    return output_path

# Concurrent: asyncio.gather() đơn giản
tasks = [_generate_audio_async(t, p, v) for t, p, v in segments]
results = await asyncio.gather(*tasks)
```

### Web Worker (Không ổn định trước khi fix)
```python
# desktop_app/audio_injector.py
from tts_edge import _generate_speech_async

# Concurrent: Semaphore + ThreadPoolExecutor phức tạp
async def _generate_one(sem, idx, text, out_path):
    async with sem:
        seg = await _generate_speech_async(text, out_path, voice, rate)
        return idx, seg

sem = asyncio.Semaphore(max_concurrent)
coros = [_generate_one(sem, idx, text, path) for ...]
results = await asyncio.gather(*coros)
```

### Điểm khác biệt chính
1. **OS recorder**: Gọi trực tiếp `edge_tts.Communicate()` trong `media_engine.py`
2. **Web worker**: Gọi qua wrapper `_generate_speech_async()` trong `tts_edge.py`
3. **OS recorder**: Dùng `asyncio.gather()` đơn giản
4. **Web worker**: Dùng Semaphore + nested async function

---

## 8. Kế hoạch tối ưu

### Phase 1: Consolidate TTS modules ✅ DONE
- [x] Thêm retry logic vào `shared/tts_edge.py`
- [x] Thêm retry logic vào `desktop_app/tts_edge.py`
- [x] Test trong Docker production

### Phase 2: Migrate to shared modules (TODO)
1. Cập nhật `desktop_app/pipeline.py` import từ `shared/` thay vì local
2. Cập nhật `desktop_app/audio_injector.py` import từ `shared/tts_edge`
3. Test web worker với shared modules
4. Xóa các bản copy không dùng trong `desktop_app/`

### Phase 3: Simplify concurrent TTS (TODO)
1. Đơn giản hóa `shared/audio_injector.py` dùng `asyncio.gather()` như OS recorder
2. Loại bỏ Semaphore phức tạp
3. Test performance và stability

### Phase 4: Clean up legacy code (TODO)
1. Xóa `src/`, `v3/`, `desktop_app/v3/` (legacy)
2. Xóa các file test cũ không dùng
3. Cập nhật documentation

---

## 9. Dependency Graph

```
Production Pipelines:
├── Web Worker (Docker)
│   └── desktop_app/* (local imports) ⚠️
│       ├── pipeline.py
│       ├── audio_injector.py
│       ├── tts_edge.py ✅ (có retry)
│       ├── bu_to_webreel.py
│       ├── trace_composer.py
│       └── webreel_runner.py
│
├── Office Worker (Docker)
│   └── desktop_app/slide_pipeline/* ⚠️ (chưa hoàn chỉnh)
│
├── OS Worker (Windows)
│   └── os_recorder/core/* ✅ (ổn định)
│       ├── os_planning_agent_v2.py
│       ├── media_engine.py (TTS trực tiếp)
│       ├── sync_recorder.py
│       └── trace_composer.py
│
└── Desktop App (Windows GUI)
    └── desktop_app/* (giống web worker)

Shared Modules (Canonical - chưa được dùng):
└── shared/*
    ├── tts_edge.py ✅ (có retry)
    ├── tts.py ✅
    ├── audio_injector.py ⚠️
    ├── bu_to_webreel.py ⚠️
    ├── trace_composer.py ⚠️
    └── webreel_runner.py ⚠️

Legacy (nên xóa):
├── src/*
├── v3/*
└── desktop_app/v3/*
```

---

## 10. Recommendations

### Ưu tiên cao
1. ✅ **DONE**: Thêm retry logic vào TTS modules đang dùng
2. **TODO**: Migrate web worker sang dùng `shared/` modules
3. **TODO**: Đơn giản hóa concurrent TTS theo pattern của OS recorder

### Ưu tiên trung bình
4. **TODO**: Hoàn thiện Office Worker pipeline
5. **TODO**: Consolidate trace_composer (3 bản copy)
6. **TODO**: Consolidate bu_to_webreel (4 bản copy)

### Ưu tiên thấp
7. **TODO**: Xóa legacy code (`src/`, `v3/`, `desktop_app/v3/`)
8. **TODO**: Cập nhật documentation
9. **TODO**: Refactor để tất cả pipeline dùng chung `shared/`

---

## 11. File Count Summary

| Module Type | Total Files | Active | Legacy | Shared (unused) |
|-------------|-------------|--------|--------|-----------------|
| tts_edge.py | 6 | 2 | 3 | 1 |
| audio_injector.py | 6 | 2 | 2 | 1 |
| bu_to_webreel.py | 4 | 1 | 2 | 1 |
| trace_composer.py | 4 | 2 | 1 | 1 |
| webreel_runner.py | 3 | 1 | 1 | 1 |
| tts.py (FPT) | 4 | 2 | 1 | 1 |

**Tổng**: 27 files trùng lặp, chỉ 10 files đang được dùng thực tế.

---

## 12. Next Steps

1. Test job hiện tại trong Docker để confirm retry logic hoạt động ✅
2. Tạo branch mới cho migration sang shared modules
3. Cập nhật imports từng bước, test sau mỗi thay đổi
4. Xóa legacy code sau khi migration hoàn tất
5. Cập nhật CI/CD và documentation
