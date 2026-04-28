# TTS Engine Options - V3 Pipeline

Pipeline V3 hỗ trợ 2 TTS engines:

## 1. FPT.AI TTS (Mặc định)
- Chất lượng giọng nói tốt, tự nhiên
- Yêu cầu API key và kết nối mạng ổn định
- Cấu hình: Đặt `FPT_API_KEY` trong file `.env`

## 2. Edge TTS (Dự phòng)
- Sử dụng Microsoft Azure TTS
- Không cần API key
- Hoạt động offline sau khi tải voice model
- Chất lượng tốt, phù hợp cho thử nghiệm

## Cách sử dụng

### Sử dụng FPT.AI TTS (mặc định)
```bash
python v3/run_pipeline_v3.py "Task description" --name video_name
```

### Sử dụng Edge TTS
```bash
python v3/run_pipeline_v3.py "Task description" --name video_name --engine edge
```

### Các tùy chọn khác
```bash
# Chọn giọng đọc
python v3/run_pipeline_v3.py "Task" --name demo --voice leminh --engine edge

# Tắt TTS (chỉ tạo video không có giọng đọc)
python v3/run_pipeline_v3.py "Task" --name demo --no-tts

# Điều chỉnh padding (khoảng dừng sau mỗi narration)
python v3/run_pipeline_v3.py "Task" --name demo --engine edge --padding 1000
```

## Giọng đọc hỗ trợ

| Voice Name | FPT.AI | Edge TTS | Mô tả |
|------------|--------|----------|-------|
| banmai | ✅ Nữ miền Bắc | ✅ vi-VN-HoaiMyNeural | Giọng mặc định |
| leminh | ✅ Nam miền Bắc | ✅ vi-VN-NamMinhNeural | Giọng nam |
| myan | ✅ Nữ miền Nam | ✅ vi-VN-HoaiMyNeural | Fallback |
| lannhi | ✅ Nữ miền Nam (trẻ) | ✅ vi-VN-HoaiMyNeural | Fallback |
| linhsan | ✅ Nữ miền Trung | ✅ vi-VN-HoaiMyNeural | Fallback |

## Cài đặt Edge TTS

Edge TTS đã được cài đặt trong venv của bạn. Nếu cần cài lại:

```bash
venv\Scripts\python.exe -m pip install edge-tts
```

## Khi nào dùng Edge TTS?

- FPT.AI bị lỗi mạng hoặc API key hết hạn
- Thử nghiệm nhanh không cần chất lượng cao nhất
- Làm việc offline hoặc mạng không ổn định
- Tiết kiệm quota API của FPT.AI

## Kiến trúc

```
v3/
├── run_pipeline_v3.py      # Main pipeline (hỗ trợ --engine flag)
├── audio_injector.py       # TTS generation (tự động chọn engine)
├── tts_edge.py            # Edge TTS implementation (NEW)
└── bu_to_webreel_v3.py    # Parser (không thay đổi)

src/
└── tts.py                 # FPT.AI TTS implementation (không thay đổi)
```

## Lưu ý

- Edge TTS có thể chậm hơn FPT.AI một chút do phải tải voice model lần đầu
- Chất lượng giọng Edge TTS khác một chút so với FPT.AI
- Cả 2 engines đều sử dụng cùng interface, dễ dàng chuyển đổi
- Audio files được lưu trong `output/{video_name}/audio/`
