# Tuan 5: Streamlit UI va Dong goi san pham

## 1. Muc tieu

Xay dung giao dien don gian de nguoi dung chi can:
1. Dan kich ban vao
2. Nhan nut "Generate Video"
3. Tai video ve

---

## 2. Kien truc

```
src/
  app.py              # Streamlit main app
  components/         # UI components (optional)
    sidebar.py        # Cau hinh TTS, output format
    preview.py        # Preview video
    history.py        # Lich su video da tao
```

---

## 3. Giao dien Streamlit

### 3.1 Layout chinh

```
+----------------------------------------------------------+
|  AI Video Tutor                                    [?]   |
+----------------------------------------------------------+
|  Sidebar          |  Main Content                        |
|  +-------------+  |  +--------------------------------+  |
|  | TTS Config  |  |  | Kich ban:                      |  |
|  | - Voice     |  |  | +----------------------------+ |  |
|  | - Speed     |  |  | | Mo Google, tim kiem       | |  |
|  | - Language  |  |  | | Python, click ket qua    | |  |
|  +-------------+  |  | | dau tien                  | |  |
|  | Output      |  |  | +----------------------------+ |  |
|  | - Format    |  |  |                                |  |
|  | - Quality   |  |  | [Generate Video]               |  |
|  +-------------+  |  +--------------------------------+  |
|  | History     |  |  | Progress:                      |  |
|  | - video1    |  |  | [################----] 80%     |  |
|  | - video2    |  |  | Step 3/4: Recording...         |  |
|  +-------------+  |  +--------------------------------+  |
|                   |  | Preview:                       |  |
|                   |  | +----------------------------+ |  |
|                   |  | |  [Video Player]            | |  |
|                   |  | +----------------------------+ |  |
|                   |  | [Download MP4]                 |  |
+----------------------------------------------------------+
```

### 3.2 Streamlit Code Structure

```python
# src/app.py
import streamlit as st
from pathlib import Path

# Page config
st.set_page_config(
    page_title="AI Video Tutor",
    page_icon="🎬",
    layout="wide",
)

# Title
st.title("AI Video Tutor")
st.markdown("Tu dong tao video huong dan tu kich ban van ban")

# Sidebar - Cau hinh
with st.sidebar:
    st.header("Cau hinh")
    
    # TTS Settings
    st.subheader("Giong doc (TTS)")
    tts_voice = st.selectbox(
        "Chon giong",
        options=[
            "vi-VN-HoaiMyNeural (Nu, Viet)",
            "vi-VN-NamMinhNeural (Nam, Viet)",
            "en-US-JennyNeural (Nu, Anh)",
        ],
        index=0,
    )
    
    tts_speed = st.slider(
        "Toc do doc",
        min_value=0.5,
        max_value=2.0,
        value=1.0,
        step=0.1,
    )
    
    # Output Settings
    st.subheader("Video output")
    output_format = st.selectbox(
        "Dinh dang",
        options=["MP4", "WebM", "GIF"],
        index=0,
    )
    
    video_quality = st.selectbox(
        "Chat luong",
        options=["1080p", "720p", "480p"],
        index=0,
    )

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    # Input
    st.subheader("Kich ban")
    script_input = st.text_area(
        "Nhap kich ban cua ban:",
        height=150,
        placeholder="Vi du: Mo trang Google, go tu khoa 'hoc lap trinh Python', nhan Enter de tim kiem",
    )
    
    # Example scripts
    with st.expander("Xem vi du kich ban"):
        st.markdown("""
        **Vi du 1: Tim kiem Google**
        ```
        Mo Google, go 'lap trinh Python cho nguoi moi bat dau', nhan Enter
        ```
        
        **Vi du 2: Dang nhap GitHub**
        ```
        Mo github.com, nhan nut Sign in, nhap email test@email.com, 
        nhap mat khau, nhan Dang nhap
        ```
        
        **Vi du 3: Tao thu muc Google Drive**
        ```
        Mo Google Drive, nhan chuot phai vao vung trong, chon New folder,
        nhap ten 'Tai lieu hoc tap', nhan Create
        ```
        """)
    
    # Generate button
    if st.button("Generate Video", type="primary", use_container_width=True):
        if not script_input.strip():
            st.error("Vui long nhap kich ban!")
        else:
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                # Step 1: Parse
                status_text.text("Buoc 1/5: Phan tich kich ban...")
                progress_bar.progress(20)
                
                # Step 2: Generate voice script
                status_text.text("Buoc 2/5: Tao loi binh...")
                progress_bar.progress(40)
                
                # Step 3: TTS
                status_text.text("Buoc 3/5: Tao audio...")
                progress_bar.progress(60)
                
                # Step 4: Record video
                status_text.text("Buoc 4/5: Quay video...")
                progress_bar.progress(80)
                
                # Step 5: Compose
                status_text.text("Buoc 5/5: Ghep video va audio...")
                progress_bar.progress(100)
                
                status_text.text("Hoan thanh!")
                st.success("Video da duoc tao thanh cong!")
                
                # Store result in session state
                st.session_state.video_path = "path/to/video.mp4"
                
            except Exception as e:
                st.error(f"Loi: {str(e)}")

with col2:
    # Preview & Download
    st.subheader("Ket qua")
    
    if "video_path" in st.session_state:
        video_path = st.session_state.video_path
        
        # Video preview
        st.video(video_path)
        
        # Download button
        with open(video_path, "rb") as f:
            st.download_button(
                label="Tai video",
                data=f,
                file_name="video_huong_dan.mp4",
                mime="video/mp4",
            )
    else:
        st.info("Video se hien thi o day sau khi tao xong")

# History (bottom)
st.divider()
st.subheader("Lich su video")

if "history" not in st.session_state:
    st.session_state.history = []

if st.session_state.history:
    for i, item in enumerate(st.session_state.history[-5:]):  # Last 5
        col1, col2, col3 = st.columns([3, 1, 1])
        with col1:
            st.text(item["script"][:50] + "...")
        with col2:
            st.text(item["created_at"])
        with col3:
            if st.button("Xem", key=f"view_{i}"):
                st.session_state.video_path = item["path"]
else:
    st.text("Chua co video nao")
```

---

## 4. Session State Management

```python
# Quan ly trang thai giua cac lan render

def init_session_state():
    """Khoi tao session state."""
    if "history" not in st.session_state:
        st.session_state.history = []
    
    if "current_job" not in st.session_state:
        st.session_state.current_job = None
    
    if "video_path" not in st.session_state:
        st.session_state.video_path = None

def add_to_history(script: str, video_path: str):
    """Them video vao lich su."""
    from datetime import datetime
    
    st.session_state.history.append({
        "script": script,
        "path": video_path,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
```

---

## 5. Background Processing

### 5.1 Van de
- Streamlit re-render moi khi co interaction
- Video generation mat nhieu thoi gian (30s - 2 phut)
- Can chay background de khong block UI

### 5.2 Giai phap: Threading + Callback

```python
import threading
from queue import Queue

# Progress queue
progress_queue = Queue()

def generate_video_background(script: str, config: dict):
    """Chay trong background thread."""
    try:
        # Step 1
        progress_queue.put(("progress", 20, "Phan tich kich ban..."))
        actions = parse_natural_language(script)
        
        # Step 2
        progress_queue.put(("progress", 40, "Tao loi binh..."))
        voice_scripts = generate_voice_script(script, actions)
        
        # Step 3
        progress_queue.put(("progress", 60, "Tao audio..."))
        audio_segments = generate_speech_batch(voice_scripts, config["output_dir"])
        
        # Step 4
        progress_queue.put(("progress", 80, "Quay video..."))
        video_path = record_video(actions, config)
        
        # Step 5
        progress_queue.put(("progress", 90, "Ghep audio..."))
        final_path = compose_video(video_path, audio_segments)
        
        progress_queue.put(("done", 100, final_path))
        
    except Exception as e:
        progress_queue.put(("error", 0, str(e)))

# Trong Streamlit
if st.button("Generate"):
    thread = threading.Thread(
        target=generate_video_background,
        args=(script_input, config),
    )
    thread.start()
    st.session_state.current_job = thread
```

---

## 6. Error Handling UI

```python
def show_error_with_suggestions(error: Exception):
    """Hien thi loi voi goi y khac phuc."""
    
    error_msg = str(error)
    
    st.error(f"Da xay ra loi: {error_msg}")
    
    # Goi y khac phuc
    with st.expander("Goi y khac phuc"):
        if "timeout" in error_msg.lower():
            st.markdown("""
            - Trang web load cham, thu lai sau
            - Kiem tra ket noi mang
            - Giam chat luong video
            """)
        
        elif "selector" in error_msg.lower():
            st.markdown("""
            - Trang web da thay doi giao dien
            - Thu mo ta element ro rang hon
            - Kiem tra trang web co yeu cau dang nhap khong
            """)
        
        elif "api" in error_msg.lower():
            st.markdown("""
            - Kiem tra API key con han khong
            - Kiem tra quota API
            - Thu doi TTS provider khac
            """)
        
        else:
            st.markdown("""
            - Thu lai voi kich ban don gian hon
            - Kiem tra kich ban co dung cu phap khong
            - Lien he ho tro neu loi van tiep tuc
            """)
```

---

## 7. Cau hinh Deploy

### 7.1 Docker Integration

```python
# Kiem tra moi truong Docker
import os

def is_docker():
    """Kiem tra dang chay trong Docker."""
    return os.path.exists("/.dockerenv")

def get_output_dir():
    """Lay thu muc output phu hop."""
    if is_docker():
        return Path("/app/output")
    return Path("./videos")
```

### 7.2 Environment Variables

```python
# .streamlit/secrets.toml (local dev)
GEMINI_API_KEY = "your-key"
OPENAI_API_KEY = "your-key"  # Optional

# Docker: truyen qua environment
# docker run -e GEMINI_API_KEY=xxx ...
```

---

## 8. Chay Streamlit

### 8.1 Local Development

```bash
cd webreel-ai-agent
streamlit run src/app.py --server.port 8501
```

### 8.2 Docker

```dockerfile
# Trong Dockerfile
CMD ["streamlit", "run", "src/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

```yaml
# docker-compose.yml
services:
  webreel-ui:
    ports:
      - "8501:8501"
```

---

## 9. Features nang cao (Optional)

### 9.1 Template Scripts

```python
TEMPLATES = {
    "google_search": {
        "name": "Tim kiem Google",
        "script": "Mo Google, go '{keyword}', nhan Enter",
        "params": ["keyword"],
    },
    "github_login": {
        "name": "Dang nhap GitHub", 
        "script": "Mo github.com/login, nhap email '{email}', nhap mat khau, nhan Sign in",
        "params": ["email"],
    },
}

# UI
template = st.selectbox("Chon template", list(TEMPLATES.keys()))
if template:
    params = {}
    for param in TEMPLATES[template]["params"]:
        params[param] = st.text_input(f"Nhap {param}")
    
    script = TEMPLATES[template]["script"].format(**params)
```

### 9.2 Export Options

```python
st.subheader("Export")

export_format = st.radio(
    "Chon dinh dang",
    ["MP4 (Video)", "GIF (Nhe, khong tieng)", "WebM (Web)"],
)

include_subtitles = st.checkbox("Them phu de", value=True)
include_voiceover = st.checkbox("Them giong doc", value=True)
```

### 9.3 Preview Steps

```python
# Hien thi preview cac buoc truoc khi generate
with st.expander("Xem truoc cac buoc"):
    actions = parse_natural_language(script_input)
    
    for i, action in enumerate(actions, 1):
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown(f"**Buoc {i}**")
        with col2:
            if action.action == "navigate":
                st.markdown(f"Mo: `{action.url}`")
            elif action.action == "click":
                st.markdown(f"Click: *{action.target}*")
            elif action.action == "type":
                st.markdown(f"Go: `{action.text}`")
```

---

## 10. Danh sach kiem tra truoc khi ban giao

- [ ] Giao dien Streamlit chay on dinh
- [ ] TTS hoat dong (it nhat 1 provider)
- [ ] Dong bo voice + video chinh xac
- [ ] Download video thanh cong
- [ ] Error handling ro rang
- [ ] Docker image build thanh cong
- [ ] 5 video mau da duoc tao
- [ ] README huong dan su dung

---

## 11. Cau truc thu muc cuoi cung

```
webreel-ai-agent/
  src/
    __init__.py
    app.py              # Streamlit UI (NEW)
    main.py             # CLI entry point
    parser.py           # NL -> Actions
    vision.py           # Vision AI locator
    locator.py          # DOM selector extraction
    generator.py        # Actions -> webreel config
    tts.py              # Text-to-Speech (NEW)
    sync.py             # Voice + Video sync (NEW)
    compose.py          # Video + Audio merge (NEW)
    models.py           # Data models
    ocr.py              # EasyOCR (optional)
  docs/
    WEEK4_TTS_SYNC.md
    WEEK5_STREAMLIT_UI.md
  .streamlit/
    config.toml         # Streamlit config
  Dockerfile
  docker-compose.yml
  requirements.txt
  README.md
```
