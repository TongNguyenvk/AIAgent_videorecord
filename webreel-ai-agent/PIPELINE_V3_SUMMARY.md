# V3 Pipeline - Tổng kết hoàn thành

## Tổng quan
V3 Pipeline là phiên bản production chính thức, thay thế hoàn toàn các pipeline cũ. Đã được tái cấu trúc và tối ưu hóa với 6 giai đoạn rõ ràng, không có AI review, sử dụng ground-truth TTS duration.

## Cấu trúc thư mục

```
webreel-ai-agent/
├── run_pipeline.py              # Main pipeline (V3)
├── src/
│   ├── audio_injector.py        # TTS generation + pause injection
│   ├── bu_to_webreel.py         # Parser: history -> config + tts_script
│   ├── trace_composer.py        # ffmpeg audio placement
│   ├── tts.py                   # FPT.AI TTS
│   ├── tts_edge.py              # Edge TTS (fallback)
│   ├── webreel_runner.py        # Webreel recording infrastructure
│   └── models.py                # Data models
├── old/                         # Deprecated files (archived)
└── v3/                          # V3 development files (reference)
```

## 6 giai đoạn Pipeline

### Phase 1: The Scout (browser-use + narration extraction)
- Chạy browser-use agent với custom action `save_narration`
- Agent đọc nội dung trang và tạo narration như giảng viên
- Output: `browser_use_history.json` với actions + narrations

### Phase 2: The Parser (config + tts_script extraction)
- Parse history thành webreel config (schema v1 compliant)
- Tạo tts_script list cho TTS generation
- Output: `webreel_pipeline.config.json`, `tts_script.json`

### Phase 3: Ground-Truth TTS (FPT.AI/Edge TTS + ffprobe)
- Generate TTS audio files (MP3)
- Đo chính xác duration bằng ffprobe (không dùng mutagen vì Edge TTS metadata sai)
- Output: `audio/narration_*.mp3` với exact duration

### Phase 4: The Injector (exact pause replacement)
- Thay thế placeholder pauses (1000ms) bằng exact TTS duration + padding
- Padding mặc định: 300ms (có thể điều chỉnh qua `--padding`)
- Output: Updated config với exact pause times

### Phase 5: The Execution (Webreel recording)
- Webreel record video với cursor animation
- Kết nối Chrome qua CDP
- Output: `videos/<name>.mp4`, `.webreel/traces/<name>.trace.json`

### Phase 6: The Composer (trace-driven ffmpeg)
- Đọc trace để lấy exact timestamps của mỗi step
- Dùng ffmpeg với `anullsrc` + `concat` để tạo silence padding
- Place MP3s tại đúng timestamps
- Output: `<name>_final.mp4`

## Cải tiến chính

### 1. Audio Sync Fix
- **Vấn đề cũ**: Mutagen đọc sai duration của Edge TTS MP3 (1/3 thực tế)
- **Giải pháp**: Dùng ffprobe để đo duration chính xác
- **Kết quả**: Audio và video sync hoàn hảo

### 2. ffmpeg Silence Padding
- **Vấn đề cũ**: `adelay` không tạo silence thực sự, chỉ delay trong filter graph
- **Giải pháp**: Dùng `anullsrc` + `concat` để tạo silence thực sự
- **Kết quả**: Audio placement chính xác tuyệt đối

### 3. Edge TTS Fallback
- **Mục đích**: Thay thế FPT.AI khi bị lỗi mạng
- **Voices**: vi-VN-HoaiMyNeural (female), vi-VN-NamMinhNeural (male)
- **Ưu điểm**: Không cần API key, hoạt động offline
- **Sử dụng**: `--engine edge`

### 4. Improved Narration Prompt
- **Vấn đề cũ**: Agent tạo narration không khớp nội dung trang
- **Cải tiến**:
  - Nhấn mạnh đọc CHÍNH XÁC nội dung trang
  - Không đoán trước nội dung trang sau
  - Phong cách tự nhiên, không lặp lại "Chào mừng"
  - Độ dài ngắn gọn (2-3 câu)
  - Tiếng Việt có dấu đầy đủ

### 5. Deduplication
- Parser tự động loại bỏ narration trùng lặp (>80% similarity)
- Tránh lặp lại narration giống hệt nhau

## Sử dụng

### Cơ bản
```bash
python run_pipeline.py "Task description" --name video_name
```

### Với Edge TTS
```bash
python run_pipeline.py "Task" --name demo --engine edge
```

### Tùy chỉnh padding
```bash
python run_pipeline.py "Task" --name demo --padding 500
```

### Tất cả options
```bash
python run_pipeline.py "Task" \
  --name demo \
  --engine edge \
  --voice banmai \
  --padding 300 \
  --no-tts
```

## Output Files

```
output/<video_name>/
├── browser_use_history.json          # Phase 1 output
├── tts_script.json                   # Phase 2 output
├── webreel_pipeline.config.json      # Phase 2 output
├── audio/
│   ├── narration_000.mp3             # Phase 3 output
│   ├── narration_001.mp3
│   └── ...
├── videos/
│   ├── <name>.mp4                    # Phase 5 output (with pauses)
│   └── <name>_raw.mp4                # Backup before compose
├── .webreel/
│   └── traces/
│       └── <name>.trace.json         # Phase 5 output
└── <name>_final.mp4                  # Phase 6 output (with audio)
```

## Kiểm tra kết quả

### Verify audio placement
```bash
python verify_audio_placement.py output/<name>/<name>_final.mp4
```

### Analyze audio sync
```bash
python analyze_audio_sync.py output/<name>
```

## Troubleshooting

### Chrome không kết nối được
```bash
# Chạy Chrome với debug port
start_chrome_debug.bat
```

### TTS generation failed
- Kiểm tra `FPT_API_KEY` trong `.env`
- Hoặc dùng Edge TTS: `--engine edge`

### Audio không sync
- Kiểm tra trace file có tồn tại không
- Verify padding value (mặc định 300ms)
- Xem log ffmpeg trong console

## So sánh với pipeline cũ

| Feature | Old Pipeline | V3 Pipeline |
|---------|-------------|-------------|
| AI Review | Có (Gemini) | Không (deterministic) |
| TTS Duration | Ước lượng | Ground-truth (ffprobe) |
| Audio Placement | MoviePy | ffmpeg + trace |
| Silence Padding | adelay (sai) | anullsrc (đúng) |
| Narration Quality | Không ổn định | Cải thiện với prompt mới |
| Deduplication | Không | Có (80% threshold) |
| Edge TTS Support | Không | Có |

## Kết luận

V3 Pipeline đã sẵn sàng cho production. Tất cả các vấn đề về audio sync đã được giải quyết. Narration quality được cải thiện đáng kể với system prompt mới.

## Tài liệu tham khảo

- `README_PIPELINE.md`: Hướng dẫn chi tiết
- `v3/AUDIO_SYNC_FIX.md`: Chi tiết về audio sync fix
- `v3/README_TTS.md`: Hướng dẫn TTS engines
- `TESTING_GUIDE.md`: Test cases
