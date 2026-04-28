"""
Streamlit UI — AI Video Tutor
Giao diện web để tạo video hướng dẫn từ mô tả tiếng Việt.

Chạy:
  cd webreel-ai-agent
  streamlit run src/app.py
"""
import asyncio
import os
import re
import threading
import time
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Import pipeline
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_pipeline_unified_chrome import run_unified_pipeline, OUTPUT_DIR


# ==============================================================================
# Page Config
# ==============================================================================
st.set_page_config(
    page_title="AI Video Tutor",
    page_icon="▶",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==============================================================================
# Constants
# ==============================================================================
EXAMPLE_SCRIPTS = {
    "Tìm kiếm Google": "Vào google.com tìm kiếm 'lập trình Python cho người mới' và dừng lại khi thấy kết quả",
    "YouTube": "Vào youtube.com tìm kiếm 'Python programming' và ấn vào video đầu tiên",
    "VnExpress": "Mở vnexpress.net, click vào bài viết tin tức đầu tiên",
    "GitHub": "Mở github.com, tìm kiếm 'react' và click vào repo đầu tiên",
}

TTS_VOICES = {
    "banmai": "Nữ miền Bắc (Ban Mai)",
    "leminh": "Nam miền Bắc (Lê Minh)",
    "myan": "Nữ miền Nam (Mỹ An)",
    "lannhi": "Nữ miền Nam trẻ (Lan Nhi)",
    "linhsan": "Nữ miền Trung (Linh San)",
}


# ==============================================================================
# Helpers
# ==============================================================================
def _slugify(text: str) -> str:
    """Chuyển text thành slug an toàn cho tên file."""
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_]+", "-", slug)
    return slug[:40].strip("-") or "demo"


def _init_session():
    """Khởi tạo session state lần đầu."""
    defaults = {
        "history": [],
        "video_path": None,
        "is_generating": False,
        "progress_step": 0,
        "progress_total": 5,
        "progress_msg": "",
        "live_logs": [],
        "error_msg": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _run_pipeline_thread(
    user_input: str,
    video_name: str,
    enable_tts: bool,
    tts_voice: str,
    enable_subtitle: bool,
    cdp_url: str = "http://localhost:9222",
):
    """Chạy pipeline trong background thread."""
    try:
        def on_progress(step, total, msg):
            st.session_state.progress_step = step
            st.session_state.progress_total = total
            st.session_state.progress_msg = msg

        # Chạy async pipeline trong thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Intercept stdout/stderr
        class LogCapturer:
            def __init__(self, original):
                self.original = original
            def write(self, message):
                self.original.write(message)
                if message.strip():
                    st.session_state.live_logs.append(message.strip())
                    if len(st.session_state.live_logs) > 50:
                        st.session_state.live_logs = st.session_state.live_logs[-50:]
            def flush(self):
                self.original.flush()
                
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = LogCapturer(old_stdout)
        sys.stderr = LogCapturer(old_stderr)

        try:
            video_path = loop.run_until_complete(run_unified_pipeline(
                task=user_input,
                video_name=video_name,
                cdp_url=cdp_url if st.session_state.get("browser_mode") == "CDP (Port 9222)" else None,
                enable_tts=enable_tts,
                tts_voice=tts_voice,
                enable_subtitle=enable_subtitle,
                on_progress=on_progress,
            ))
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

        st.session_state.video_path = str(video_path)
        st.session_state.history.insert(0, {
            "script": user_input,
            "path": str(video_path),
            "name": video_name,
            "created_at": datetime.now().strftime("%d/%m/%Y %H:%M"),
            "has_tts": enable_tts,
        })
        st.session_state.error_msg = None

    except Exception as exc:
        import traceback
        st.session_state.error_msg = f"{exc}\n\n{traceback.format_exc()}"
        st.session_state.video_path = None

    finally:
        st.session_state.is_generating = False
        st.session_state.progress_step = 0
        st.session_state.progress_msg = ""


# ==============================================================================
# CSS tùy chỉnh với Dark Mode support
# ==============================================================================
st.markdown("""
<style>
    /* Root variables */
    :root {
        --primary-blue: #2563eb;
        --success-green: #10b981;
        --warning-orange: #f59e0b;
    }
    
    /* Tabs styling - Universal */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 2px solid rgba(128, 128, 128, 0.2);
    }
    .stTabs [data-baseweb="tab"] {
        padding: 12px 24px;
        font-size: 15px;
        font-weight: 500;
        border-radius: 8px 8px 0 0;
        background: transparent;
        transition: all 0.2s;
    }
    .stTabs [data-baseweb="tab"]:hover {
        background: rgba(37, 99, 235, 0.1);
    }
    .stTabs [aria-selected="true"] {
        background: var(--primary-blue) !important;
        color: white !important;
    }
    
    /* Step items - Universal with opacity */
    .step-item {
        padding: 10px 16px;
        margin: 6px 0;
        border-radius: 6px;
        font-size: 14px;
        border-left: 3px solid transparent;
        transition: all 0.2s;
    }
    
    .step-done { 
        background: rgba(16, 185, 129, 0.15); 
        color: var(--success-green); 
        border-left-color: var(--success-green);
    }
    .step-active { 
        background: rgba(245, 158, 11, 0.15); 
        color: var(--warning-orange); 
        border-left-color: var(--warning-orange);
        font-weight: 500;
    }
    .step-pending { 
        background: rgba(128, 128, 128, 0.1); 
        color: rgba(128, 128, 128, 0.7); 
        border-left-color: rgba(128, 128, 128, 0.3);
    }
    
    /* Buttons */
    .stButton > button {
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 6px rgba(0,0,0,0.15);
    }
    
    /* Input fields */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border-radius: 6px;
        transition: all 0.2s;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--primary-blue);
        box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        border-radius: 6px;
        transition: all 0.2s;
    }
    .streamlit-expanderHeader:hover {
        background: rgba(37, 99, 235, 0.05);
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        font-size: 1.5rem;
        font-weight: 600;
    }
    
    /* Progress bar */
    .stProgress > div > div > div {
        background-color: var(--primary-blue);
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# MAIN UI
# ==============================================================================
_init_session()


# ---- Sidebar ----
with st.sidebar:
    st.title("Cấu hình")

    # --- LLM Provider ---
    st.subheader("LLM Provider")
    gemini_key = st.text_input(
        "GEMINI_API_KEY",
        value=os.environ.get("GEMINI_API_KEY", ""),
        type="password",
        help="Lấy tại https://aistudio.google.com/app/apikey",
    )
    if gemini_key:
        os.environ["GEMINI_API_KEY"] = gemini_key
        os.environ["GOOGLE_API_KEY"] = gemini_key

    st.divider()

    # --- Browser Mode ---
    st.subheader("Browser Mode")
    browser_mode = st.radio(
        "Chế độ trình duyệt:",
        ["Headless (Ẩn)", "CDP (Port 9222)"],
        index=1,
        help="Sử dụng CDP để kết nối vào Chrome đang mở sẵn (chống bot tốt hơn)."
    )
    st.session_state["browser_mode"] = browser_mode
    
    cdp_url = "http://localhost:9222"
    if browser_mode == "CDP (Port 9222)":
        cdp_url = st.text_input("CDP Endpoint:", value="http://localhost:9222")

    st.divider()

    # --- TTS Config ---
    st.subheader("Thuyết minh (TTS)")
    enable_tts = st.toggle("Bật thuyết minh giọng nói", value=True)

    tts_voice = "banmai"
    enable_subtitle = False

    if enable_tts:
        tts_voice = st.selectbox(
            "Chọn giọng:",
            options=list(TTS_VOICES.keys()),
            format_func=lambda v: TTS_VOICES[v],
            index=0,
        )
        enable_subtitle = st.checkbox("Thêm phụ đề", value=False)

    st.divider()

    # --- Lịch sử ---
    st.subheader("Lịch sử video")
    if st.session_state.history:
        for i, item in enumerate(st.session_state.history[:8]):
            col_info, col_btn = st.columns([3, 1])
            with col_info:
                st.caption(item["created_at"])
                tts_badge = " [TTS]" if item.get("has_tts") else ""
                st.markdown(f"**{item['name']}**{tts_badge}")
            with col_btn:
                if st.button("Play", key=f"hist_{i}", use_container_width=True):
                    st.session_state.video_path = item["path"]
                    st.rerun()
    else:
        st.caption("Chưa có video nào.")

    st.divider()
    st.caption("AI Video Tutor v2.0")


# ---- Main Content ----
st.title("AI Video Tutor")
st.markdown(
    "Nhập kịch bản bằng ngôn ngữ tự nhiên, AI sẽ tự động mở trình duyệt, "
    "quay video thực hành, và thêm thuyết minh giọng nói cho bạn."
)

tab_create, tab_result = st.tabs(["Tạo video", "Kết quả"])


# ---- Tab 1: Tạo video ----
with tab_create:
    col_input, col_examples = st.columns([3, 2])

    with col_input:
        st.subheader("Kịch bản của bạn")

        script_input = st.text_area(
            label="Nhập kịch bản:",
            height=160,
            placeholder=(
                "Ví dụ: Vào google.com tìm kiếm 'lập trình Python' và dừng lại khi thấy kết quả\n\n"
                "Hoặc: Mở youtube.com, tìm kiếm 'Python programming' và ấn vào video đầu tiên"
            ),
            label_visibility="collapsed",
        )

        col_name, col_btn = st.columns([2, 1])
        with col_name:
            video_name_input = st.text_input(
                "Tên video:",
                value=_slugify(script_input) if script_input else "demo",
                help="Tên file và key trong config",
            )

        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            generate_btn = st.button(
                "Generate",
                type="primary",
                use_container_width=True,
                disabled=st.session_state.is_generating,
            )

    with col_examples:
        st.subheader("Ví dụ mẫu")
        for label, example in EXAMPLE_SCRIPTS.items():
            if st.button(label, use_container_width=True, key=f"ex_{label}"):
                st.session_state["_example_script"] = example
                st.rerun()

    # Set script from example click
    if "_example_script" in st.session_state:
        script_input = st.session_state.pop("_example_script")

    # --- Xử lý Generate ---
    if generate_btn:
        if not script_input.strip():
            st.error("Vui lòng nhập kịch bản trước khi tạo video.")
        elif not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
            st.error("Cần GEMINI_API_KEY ở thanh bên trái.")
        else:
            video_name = video_name_input.strip() or _slugify(script_input)
            st.session_state.is_generating = True
            st.session_state.error_msg = None
            st.session_state.video_path = None
            st.session_state.progress_step = 0
            st.session_state.progress_msg = "Đang khởi động..."
            st.session_state.live_logs = []

            thread = threading.Thread(
                target=_run_pipeline_thread,
                args=(script_input, video_name, enable_tts, tts_voice, enable_subtitle, cdp_url),
                daemon=True,
            )
            thread.start()
            st.rerun()

    # --- Progress UI ---
    if st.session_state.is_generating:
        st.info("Video đang được tạo, vui lòng chờ...")

        step = st.session_state.progress_step
        total = st.session_state.progress_total
        msg = st.session_state.progress_msg

        progress_val = step / total if total > 0 else 0
        st.progress(progress_val, text=f"Bước {step}/{total}: {msg}")

        step_labels = [
            "Browser-use Agent thực hiện task",
            "Chuyển đổi actions sang webreel config",
            "Quay video với webreel",
            "Sinh thuyết minh TTS",
            "Ghép video và audio (MoviePy)",
            "Hoàn thiện"
        ]

        for i, label in enumerate(step_labels, 1):
            if i < step:
                st.markdown(f'<div class="step-item step-done">[DONE] {label}</div>', unsafe_allow_html=True)
            elif i == step:
                st.markdown(f'<div class="step-item step-active">[RUNNING] {label}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="step-item step-pending">[PENDING] {label}</div>', unsafe_allow_html=True)

        # Show live logs
        with st.expander("Live Logs (Terminal)", expanded=True):
            log_text = "\\n".join(st.session_state.live_logs)
            st.code(log_text, language="bash")

        # Tự động refresh
        time.sleep(2)
        st.rerun()

    # --- Error UI ---
    if st.session_state.error_msg:
        error = st.session_state.error_msg
        st.error("Đã xảy ra lỗi!")
        with st.expander("Chi tiết lỗi"):
            st.code(error)

        with st.expander("Gợi ý khắc phục"):
            if "quota" in error.lower() or "rate" in error.lower():
                st.markdown("- API quota hết, thử lại sau ít phút hoặc đổi API key")
            elif "timeout" in error.lower():
                st.markdown("- Trang web load chậm, thử lại sau")
            elif "webreel" in error.lower():
                st.markdown("- Kiểm tra webreel đã được build chưa: `pnpm build`")
            elif "fpt" in error.lower() or "tts" in error.lower():
                st.markdown("- Kiểm tra FPT_TTS_API_KEY trong file .env")
            else:
                st.markdown("- Thử kịch bản đơn giản hơn")
                st.markdown("- Kiểm tra API key còn hiệu lực")

    # --- Success notification ---
    if (
        st.session_state.video_path
        and not st.session_state.is_generating
        and not st.session_state.error_msg
    ):
        st.success("Video tạo thành công! Xem ở tab Kết quả.")


# ---- Tab 2: Kết quả ----
with tab_result:
    st.subheader("Video đã tạo")

    video_path = st.session_state.video_path
    if video_path and Path(video_path).exists():
        st.video(video_path)

        col_dl, col_info = st.columns([1, 2])
        with col_dl:
            with open(video_path, "rb") as f:
                st.download_button(
                    label="Tải video (MP4)",
                    data=f,
                    file_name=Path(video_path).name,
                    mime="video/mp4",
                    use_container_width=True,
                )
        with col_info:
            size_mb = Path(video_path).stat().st_size / 1024 / 1024
            st.metric("Kích thước", f"{size_mb:.1f} MB")
            st.metric("File", Path(video_path).name)

            # Kiểm tra xem có video gốc không (khi có TTS)
            parent = Path(video_path).parent
            raw_videos = list(parent.glob("*.mp4"))
            if len(raw_videos) > 1:
                st.caption(f"Thư mục output: {parent}")

    elif video_path:
        st.warning(f"File video không tồn tại: {video_path}")
    else:
        st.info("Chưa có video. Tạo video ở tab Tạo video.")
