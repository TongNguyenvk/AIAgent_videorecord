# Tuan 4: Voiceover (TTS) va Dong bo hoa

## 1. Muc tieu

Them loi binh (voiceover) cho video de nguoi xem hieu ro tung buoc thao tac.

**Ket qua mong doi:**
- Video co giong doc huong dan di kem
- Loi noi dong bo voi hanh dong tren man hinh (vi du: "Bay gio ban nhan vao nut nay" khop voi luc chuot dang nhan)

---

## 2. Kien truc Module

```
src/
  tts.py          # Text-to-Speech: Chuyen van ban thanh audio
  sync.py         # Dong bo hoa: Tinh thoi diem phat am cho tung action
  compose.py      # Ghep video + audio thanh video hoan chinh
```

---

## 3. Module TTS (tts.py)

### 3.1 Chuc nang
- Nhan van ban tieng Viet/Anh
- Tra ve file audio (.mp3/.wav)
- Ho tro nhieu TTS provider

### 3.2 TTS Providers

| Provider | Uu diem | Nhuoc diem | API |
|----------|---------|------------|-----|
| **Google TTS (gTTS)** | Mien phi, de dung | Giong may, khong tu nhien | `gtts` package |
| **OpenAI TTS** | Giong rat tu nhien | Tra phi, can API key | `openai.audio.speech` |
| **FPT.AI** | Giong Viet chuan | Tra phi, can dang ky | REST API |
| **Edge TTS** | Mien phi, giong tot | Can mang | `edge-tts` package |

### 3.3 Interface

```python
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

class TTSProvider(Enum):
    GOOGLE = "google"      # gTTS - mien phi
    OPENAI = "openai"      # OpenAI TTS - tra phi
    EDGE = "edge"          # Edge TTS - mien phi, giong tot
    FPT = "fpt"            # FPT.AI - tieng Viet

@dataclass
class TTSConfig:
    provider: TTSProvider = TTSProvider.EDGE
    language: str = "vi"           # vi, en
    voice: str = "vi-VN-HoaiMyNeural"  # Edge TTS voice
    speed: float = 1.0             # 0.5 - 2.0

@dataclass 
class AudioSegment:
    text: str                      # Van ban goc
    audio_path: Path               # Duong dan file audio
    duration_ms: int               # Do dai audio (ms)

def generate_speech(
    text: str,
    output_path: Path,
    config: TTSConfig = TTSConfig(),
) -> AudioSegment:
    """
    Chuyen van ban thanh file audio.
    
    Args:
        text: Van ban can doc
        output_path: Duong dan luu file audio
        config: Cau hinh TTS
        
    Returns:
        AudioSegment voi thong tin audio da tao
    """
    pass

def generate_speech_batch(
    texts: list[str],
    output_dir: Path,
    config: TTSConfig = TTSConfig(),
) -> list[AudioSegment]:
    """
    Tao audio cho nhieu doan van ban.
    """
    pass
```

### 3.4 Edge TTS Voices (Khuyen dung)

**Tieng Viet:**
- `vi-VN-HoaiMyNeural` - Nu, trang trong
- `vi-VN-NamMinhNeural` - Nam, chuyen nghiep

**Tieng Anh:**
- `en-US-JennyNeural` - Nu, than thien
- `en-US-GuyNeural` - Nam, chuyen nghiep

---

## 4. Module Sync (sync.py)

### 4.1 Van de can giai quyet

**Thu thach:** Lam sao de loi noi "Bay gio ban nhan vao nut tim kiem" phat dung luc chuot di chuyen den nut do?

**Giai phap:** Tinh toan timeline cho tung action va voice segment.

### 4.2 Cach tiep can

```
Timeline Video:
|--pause(1000ms)--|--moveTo--|--pause(400ms)--|--click--|--pause(600ms)--|--type--|...
     0ms            1000ms      1200ms           1600ms     2200ms          2800ms

Timeline Voice:
|----"Mo trang Google"----|-pause-|----"Nhan vao o tim kiem"----|-pause-|----"Go tu khoa"-----|
     0ms                   1500ms      2000ms                     3500ms      4000ms
```

### 4.3 Interface

```python
from dataclasses import dataclass

@dataclass
class VoiceSegment:
    text: str                    # Loi doc
    start_ms: int                # Thoi diem bat dau (ms)
    duration_ms: int             # Do dai (ms)
    action_index: int            # Lien ket voi action nao

@dataclass
class SyncedTimeline:
    video_duration_ms: int       # Tong do dai video
    voice_segments: list[VoiceSegment]
    audio_path: Path             # File audio da ghep

def calculate_action_timings(
    steps: list[WebreelStep],
) -> list[tuple[int, int]]:
    """
    Tinh thoi diem bat dau va ket thuc cua tung step.
    
    Returns:
        List of (start_ms, end_ms) cho tung step
    """
    pass

def generate_voice_script(
    user_input: str,
    actions: list[ParsedAction],
) -> list[str]:
    """
    Su dung LLM de tao loi binh cho tung action.
    
    Input: "Tim kiem Python tren Google"
    Actions: [navigate, type, key]
    
    Output: [
        "Dau tien, chung ta mo trang Google",
        "Tiep theo, go tu khoa Python vao o tim kiem", 
        "Cuoi cung, nhan Enter de tim kiem"
    ]
    """
    pass

def sync_voice_with_actions(
    actions: list[ParsedAction],
    action_timings: list[tuple[int, int]],
    voice_segments: list[AudioSegment],
) -> SyncedTimeline:
    """
    Dong bo voice voi action dua tren timing.
    
    Logic:
    1. Voice bat dau TRUOC action 500ms (de nguoi xem chuan bi)
    2. Neu voice dai hon action, keo dai pause sau action
    3. Neu voice ngan hon action, them im lang
    """
    pass
```

### 4.4 Chien luoc dong bo

**Option A: Voice truoc Action (Khuyen dung)**
```
Voice: "Bay gio nhan vao nut tim kiem"
        |---------------------------|
Action:              |--click--|
                     ^
                     Voice ket thuc truoc khi click
```

**Option B: Voice trong khi Action**
```
Voice: "Nhan vao day"
        |-----------|
Action: |--click--|
        ^
        Bat dau cung luc
```

**Option C: Voice sau Action**
```
Action: |--click--|
Voice:            "Da nhan xong"
                  |-------------|
```

---

## 5. Module Compose (compose.py)

### 5.1 Chuc nang
- Ghep video (tu webreel) voi audio (tu TTS)
- Dieu chinh do dai video neu can
- Xuat video cuoi cung

### 5.2 Interface

```python
from pathlib import Path

def compose_video_with_audio(
    video_path: Path,           # Video tu webreel (khong co tieng)
    synced_timeline: SyncedTimeline,
    output_path: Path,
    add_background_music: bool = False,
    music_volume: float = 0.1,  # 0.0 - 1.0
) -> Path:
    """
    Ghep video voi audio da dong bo.
    
    Su dung MoviePy:
    1. Load video
    2. Load audio segments
    3. Dat audio vao dung thoi diem
    4. Xuat video moi
    """
    pass

def extend_video_if_needed(
    video_path: Path,
    target_duration_ms: int,
) -> Path:
    """
    Keo dai video (freeze frame cuoi) neu audio dai hon video.
    """
    pass

def add_subtitles(
    video_path: Path,
    voice_segments: list[VoiceSegment],
    output_path: Path,
    font_size: int = 24,
    position: str = "bottom",  # top, center, bottom
) -> Path:
    """
    Them phu de vao video (optional).
    """
    pass
```

### 5.3 MoviePy Code Example

```python
from moviepy.editor import (
    VideoFileClip, 
    AudioFileClip, 
    CompositeAudioClip,
    concatenate_audioclips,
)

def compose_video_with_audio(video_path, audio_segments, output_path):
    # Load video
    video = VideoFileClip(str(video_path))
    
    # Tao audio clips voi timing
    audio_clips = []
    for segment in audio_segments:
        audio = AudioFileClip(str(segment.audio_path))
        audio = audio.set_start(segment.start_ms / 1000)  # Convert to seconds
        audio_clips.append(audio)
    
    # Ghep tat ca audio
    final_audio = CompositeAudioClip(audio_clips)
    
    # Gan audio vao video
    final_video = video.set_audio(final_audio)
    
    # Xuat
    final_video.write_videofile(
        str(output_path),
        codec="libx264",
        audio_codec="aac",
        fps=30,
    )
    
    return output_path
```

---

## 6. Flow tong the

```
User Input: "Tim kiem Python tren Google"
                    |
                    v
    +----------------------------------+
    |  1. Parser (da co)               |
    |  NL -> Actions JSON              |
    +----------------------------------+
                    |
                    v
    +----------------------------------+
    |  2. Voice Script Generator       |
    |  LLM tao loi binh cho tung action|
    +----------------------------------+
                    |
                    v
    +----------------------------------+
    |  3. TTS Module                   |
    |  Van ban -> Audio files          |
    +----------------------------------+
                    |
                    v
    +----------------------------------+
    |  4. Vision + Locator (da co)     |
    |  Tim selector cho tung action    |
    +----------------------------------+
                    |
                    v
    +----------------------------------+
    |  5. Generator (da co)            |
    |  Actions -> webreel.config.json  |
    +----------------------------------+
                    |
                    v
    +----------------------------------+
    |  6. Webreel Record               |
    |  Config -> Video (khong tieng)   |
    +----------------------------------+
                    |
                    v
    +----------------------------------+
    |  7. Sync Module                  |
    |  Tinh timing cho voice           |
    +----------------------------------+
                    |
                    v
    +----------------------------------+
    |  8. Compose Module               |
    |  Video + Audio -> Final Video    |
    +----------------------------------+
                    |
                    v
            Final Video.mp4
            (co hinh + co tieng)
```

---

## 7. Dependencies can them

```txt
# TTS
edge-tts>=6.1.0          # Microsoft Edge TTS (mien phi, giong tot)
gtts>=2.3.0              # Google TTS (mien phi, backup)
openai>=1.0.0            # OpenAI TTS (optional, tra phi)

# Video/Audio processing
moviepy>=1.0.3           # Ghep video + audio
pydub>=0.25.1            # Xu ly audio (cat, ghep, do dai)

# Subtitles (optional)
srt>=3.5.0               # Tao file phu de
```

---

## 8. Test Cases

### Test 1: TTS don gian
```python
from src.tts import generate_speech, TTSConfig

config = TTSConfig(provider="edge", voice="vi-VN-HoaiMyNeural")
segment = generate_speech(
    "Xin chao, day la video huong dan",
    Path("test_audio.mp3"),
    config
)
assert segment.duration_ms > 0
assert segment.audio_path.exists()
```

### Test 2: Sync timing
```python
from src.sync import calculate_action_timings

steps = [
    WebreelStep(action="pause", ms=1000),
    WebreelStep(action="click", selector="#btn", delay=600),
    WebreelStep(action="pause", ms=500),
]

timings = calculate_action_timings(steps)
# Expected: [(0, 1000), (1000, 1600), (1600, 2100)]
```

### Test 3: Full compose
```python
from src.compose import compose_video_with_audio

result = compose_video_with_audio(
    video_path=Path("demo.mp4"),
    synced_timeline=timeline,
    output_path=Path("demo_with_voice.mp4"),
)
assert result.exists()
```
