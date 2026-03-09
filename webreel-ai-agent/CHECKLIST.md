# Project Checklist - AI Video Tutor

## DA XONG

- [x] `src/models.py` - Pydantic models (ParsedAction, ResolvedAction, Coordinates)
- [x] `src/parser.py` - NL parser, hybrid backend: Gemini (neu co) -> Azure fallback
- [x] `src/vision.py` - Vision AI, hybrid backend: Gemini (neu co) -> Azure fallback
- [x] `src/locator.py` - CSS selector extraction tu Playwright DOM
- [x] `src/generator.py` - Sinh webreel.config.json tu resolved actions
- [x] `src/tts.py` - FPT.AI TTS module (da test, hoat dong)
  - `generate_speech(text, path, voice, speed, api_key)` - tao 1 file MP3
  - `generate_speech_batch(texts, dir)` - tao nhieu file MP3
  - `build_narration_texts(actions)` - tu actions -> van ban thuyet minh
  - `FPT_TTS_API_KEY` da them vao `.env`
- [x] `src/pipeline.py` - Them Step 5 TTS (tu dong kich hoat neu FPT_TTS_API_KEY co trong .env)
  - [x] Nhan `on_progress` callback de Streamlit co the theo doi
  - [x] `MOCK_MODE=1` hoat dong (test xong, khong can API hay browser)
- [x] `src/main.py` - CLI entry point (25 lines), goi pipeline.py
- [x] `src/app.py` - Streamlit UI voi 3 tab: Tao video / Xem truoc / Ket qua
  - [x] Sidebar: nhap API key, lich su video
  - [x] Progress bar tu background thread
  - [x] Mock mode banner khi MOCK_MODE=1
  - [x] Azure fallback (khong bat buoc phai co Gemini key)
  - [x] Download button cho video MP4
- [x] `.streamlit/config.toml` - Dark theme, port 8501
- [x] `Dockerfile` - Playwright base, Node 20, FFmpeg, Streamlit, port 8501
- [x] `docker-compose.yml` - port 8501, shm 2gb, env vars
- [x] `requirements.txt` - Tat ca dep khai bao du
- [x] `.env` - GITHUB_TOKEN, GEMINI_API_KEY, CHROME_HEADLESS_PATH, FFMPEG_PATH
- [x] `docs/WEEK4_TTS_SYNC.md` + `docs/WEEK5_STREAMLIT_UI.md`

---

## CAN LAM KHI CO MANG

### 1. Cai package con thieu (bat buoc)

```bash
cd webreel-ai-agent
.\venv\Scripts\pip.exe install streamlit google-generativeai
```

Kiem tra sau khi cai:

```bash
.\venv\Scripts\python.exe -c "import streamlit, google.generativeai; print('OK')"
```

### 2. Chay Streamlit UI lan dau

```bash
# Tu thu muc webreel-ai-agent
.\venv\Scripts\streamlit.exe run src/app.py
# Mo trinh duyet: http://localhost:8501
```

Test voi MOCK_MODE truoc (khong can API):

```bash
$env:MOCK_MODE="1"
.\venv\Scripts\streamlit.exe run src/app.py
```

### 3. Test API thuc

```bash
# Test Gemini
.\venv\Scripts\python.exe -c "
import google.generativeai as genai
genai.configure(api_key='AIzaSyCeJxglaNh4igJDv9kFiKv0FqdYaNfQico')
r = genai.GenerativeModel('gemini-2.0-flash').generate_content('Say hello')
print(r.text)
"

# Test Azure (GitHub quota hay het, co the dung Gemini thay)
.\venv\Scripts\python.exe -c "
import os; from dotenv import load_dotenv; load_dotenv()
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import UserMessage
from azure.core.credentials import AzureKeyCredential
c = ChatCompletionsClient('https://models.github.ai/inference', AzureKeyCredential(os.environ['GITHUB_TOKEN']))
r = c.complete(messages=[UserMessage('Say hello')], model='meta/Llama-4-Scout-17B-16E-Instruct', max_tokens=10)
print(r.choices[0].message.content)
"
```

### 4. Build webreel (can fix Windows)

Van de: `package.json` dung `rm -rf dist` (lenh Linux, khong chay tren Windows cmd).

Fix: Sua script trong `packages/webreel/package.json`:

```json
"build": "rimraf dist && tsc"
```

Cai rimraf:

```bash
pnpm add -D rimraf --filter webreel
pnpm build
```

Hoac dung PowerShell natively:

```bash
# Trong packages/webreel/package.json doi "rm -rf dist" thanh:
"build": "pwsh -c 'Remove-Item -Recurse -Force dist -ErrorAction Ignore' && tsc"
```

### 5. Test pipeline day du (real API + browser)

```bash
cd webreel-ai-agent
.\venv\Scripts\python.exe -m src.main "Mo google.com, go 'Python tutorial', nhan Enter" --name test-real
```

Ket qua mong doi:
- Tao `webreel.config.json` trong thu muc goc
- Chrome mo va ghi man hinh
- Xuat file `videos/test-real.mp4`

### 6. EasyOCR (OCR fallback khi Vision AI khong nhan dien duoc)

Da cai (`pip install easyocr` exit 0) nhung model chua download. Lan dau chay se tu dong download:

```bash
.\venv\Scripts\python.exe -c "import easyocr; r = easyocr.Reader(['en', 'vi']); print('EasyOCR OK')"
# Mat 2-3 phut download model ~200MB
```

### 7. Docker (deployment cuoi)

```bash
# Tu thu muc goc webreel/
docker compose -f webreel-ai-agent/docker-compose.yml up --build
# Mo: http://localhost:8501
```

---

## TRANG THAI API / BACKEND

| Backend | Trang thai | Ghi chu |
|---------|-----------|---------|
| Gemini (`google-generativeai`) | Chua cai duoc | Net timeout khi pip install |
| Azure GitHub Models | Loi quota (exit 1) | GitHub token van hop le |
| MOCK_MODE | Hoat dong tot | Dung de test UI, khong can net |
| Playwright/Chromium | Hoat dong | Path: `C:\Users\admin\AppData\Local\ms-playwright\...` |
| FFmpeg | Hoat dong | Path: `C:\ProgramData\chocolatey\bin\ffmpeg.exe` |
| EasyOCR | Da cai, chua download model | Tu dong download khi chay lan dau |

---

## FILE QUAN TRONG

```
webreel-ai-agent/
  src/
    parser.py    <- Hybrid Gemini/Azure, parse NL thanh actions
    vision.py    <- Hybrid Gemini/Azure, tim toa do element
    locator.py   <- Lay CSS selector tu toa do
    generator.py <- Tao webreel.config.json
    pipeline.py  <- Gom het, co MOCK_MODE
    main.py      <- CLI (25 lines)
    app.py       <- Streamlit UI
  .env           <- API keys va paths
  requirements.txt
  Dockerfile
  docker-compose.yml
```
