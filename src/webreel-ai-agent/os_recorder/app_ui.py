"""
OS Recorder - Streamlit Test UI (Phase 1)
Giao dien test co ban: chon cua so, nhap prompt, sinh ke hoach.
"""

import streamlit as st
import sys
import os
from pathlib import Path

# Them thu muc hien tai vao path
sys.path.insert(0, str(Path(__file__).parent))

from core.window_manager import get_visible_windows, get_window_rect_by_pid, cleanup_workspace


def main():
    st.set_page_config(
        page_title="OS Recorder - Test UI",
        page_icon="🎬",
        layout="wide",
    )

    st.title("OS Recorder - Test UI")
    st.caption("Prototype quay man hinh cap do OS")

    # --- Sidebar: Cau hinh ---
    with st.sidebar:
        st.header("Cau hinh")

        if st.button("Lam moi danh sach cua so", use_container_width=True):
            st.session_state["windows"] = get_visible_windows()

        # Lay danh sach cua so
        if "windows" not in st.session_state:
            st.session_state["windows"] = get_visible_windows()

        windows = st.session_state["windows"]

        st.info(f"Tim thay {len(windows)} cua so")

        # Dropdown chon cua so (hien thi title, gia tri la index)
        window_options = {
            f"{w['title']} (PID: {w['pid']})": i
            for i, w in enumerate(windows)
        }

        if window_options:
            selected_label = st.selectbox(
                "Chon cua so muc tieu",
                options=list(window_options.keys()),
            )
            selected_idx = window_options[selected_label]
            selected_window = windows[selected_idx]

            st.write(f"**PID:** {selected_window['pid']}")
            st.write(f"**HWND:** {selected_window['hwnd']}")

            # Hien thi bounding box
            rect = get_window_rect_by_pid(selected_window["pid"])
            if rect:
                left, top, width, height = rect
                st.write(f"**Vi tri:** ({left}, {top})")
                st.write(f"**Kich thuoc:** {width} x {height}")
        else:
            st.warning("Khong tim thay cua so nao!")
            selected_window = None

    # --- Main area ---
    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("Nhiem vu")
        user_prompt = st.text_area(
            "Mo ta nhiem vu can thuc hien",
            placeholder="VD: Trinh chieu PowerPoint tu slide 1 den slide 10, moi slide dung 5 giay",
            height=120,
        )

        col_btn1, col_btn2, col_btn3 = st.columns(3)

        with col_btn1:
            btn_capture = st.button(
                "Chup man hinh",
                use_container_width=True,
                disabled=selected_window is None,
            )

        with col_btn2:
            btn_plan = st.button(
                "Sinh ke hoach (AI)",
                use_container_width=True,
                disabled=selected_window is None,
                type="primary",
            )

        with col_btn3:
            btn_record = st.button(
                "Quay thu (5s)",
                use_container_width=True,
                disabled=selected_window is None,
            )

    with col2:
        st.subheader("Trang thai")
        status_container = st.container()

    # --- Actions ---

    # Chup man hinh
    if btn_capture and selected_window:
        with st.spinner("Dang chup man hinh..."):
            try:
                from core.vision_agent import capture_window_by_pid
                screenshot_path = capture_window_by_pid(
                    selected_window["pid"],
                    "workspace/temp_screenshot.png",
                )
                st.image(screenshot_path, caption=f"Screenshot: {selected_window['title']}")
                with status_container:
                    st.success(f"Da chup: {screenshot_path}")
            except Exception as e:
                with status_container:
                    st.error(f"Loi chup man hinh: {e}")

    # Sinh ke hoach AI
    if btn_plan and selected_window and user_prompt:
        with st.spinner("Dang goi Gemini de sinh ke hoach..."):
            try:
                from core.vision_agent import capture_window_by_pid, generate_action_plan, save_action_plan

                # Chup man hinh truoc
                screenshot_path = capture_window_by_pid(
                    selected_window["pid"],
                    "workspace/temp_screenshot.png",
                )

                # Goi AI
                actions = generate_action_plan(screenshot_path, user_prompt)
                plan_path = save_action_plan(actions)

                st.subheader("Ke hoach hanh dong")
                for i, action in enumerate(actions):
                    action_type = action.get("action_type", "")
                    target = action.get("target_value", "")
                    duration = action.get("estimated_duration_ms", 0)

                    if action_type == "speak":
                        st.write(f"**{i+1}.** 🎤 Noi: _{target}_ ({duration}ms)")
                    elif action_type == "press_key":
                        st.write(f"**{i+1}.** ⌨️ Bam phim: `{target}` ({duration}ms)")
                    elif action_type == "wait":
                        st.write(f"**{i+1}.** ⏳ Cho: {target} ({duration}ms)")

                with status_container:
                    st.success(f"Da sinh {len(actions)} hanh dong. Luu tai: {plan_path}")
            except Exception as e:
                with status_container:
                    st.error(f"Loi sinh ke hoach: {e}")

    elif btn_plan and not user_prompt:
        with status_container:
            st.warning("Vui long nhap mo ta nhiem vu truoc!")

    # Quay thu 5 giay
    if btn_record and selected_window:
        with st.spinner("Dang quay man hinh (5 giay)..."):
            try:
                from core.media_engine import start_screen_recording, stop_recording
                import time

                video_path = "workspace/test_recording.mp4"
                process = start_screen_recording(
                    selected_window["pid"],
                    video_path,
                )

                if process:
                    time.sleep(5)
                    stop_recording(process)

                    with status_container:
                        st.success(f"Da quay xong: {video_path}")
                    st.video(video_path)
                else:
                    with status_container:
                        st.error("Khong the bat dau quay. Kiem tra FFmpeg da cai dat chua.")
            except Exception as e:
                with status_container:
                    st.error(f"Loi quay man hinh: {e}")

    # --- Footer ---
    st.divider()
    st.caption("OS Recorder v0.1 - Test UI | Phase 1 Prototype")


if __name__ == "__main__":
    main()
