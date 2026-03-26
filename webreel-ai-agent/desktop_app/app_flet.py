"""
AI Video Tutor - Desktop App (Flet UI)
Standalone version with multi-threading and job control
"""

import flet as ft
import asyncio
import logging
import threading
from pathlib import Path
from pipeline import run_pipeline_v3
from dotenv import load_dotenv
import os
import subprocess
import platform
from datetime import datetime
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DESKTOP_APP_DIR = Path(__file__).parent
env_path = DESKTOP_APP_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)





def check_chrome_running(port: int = 9222) -> bool:
    """Check if Chrome CDP is running on a specific port."""
    cdp_url = f"http://localhost:{port}"
    try:
        response = requests.get(f"{cdp_url}/json/version", timeout=1)
        return response.status_code == 200
    except:
        return False


def launch_chrome_with_cdp(port: int = 9222) -> str:
    """Launch Chrome with CDP on a specific port."""
    from browser_launcher import launch_chrome_with_cdp as _launch
    return _launch(port=port, kill_existing=False)


def main(page: ft.Page):
    page.title = "AI Video Tutor"
    page.window.width = 1280
    page.window.height = 720
    page.padding = 0
    page.scroll = None
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = ft.Colors.GREY_50
    
    # State
    running_jobs = {}
    job_counter = 0
    current_tab = 0
    
    # Phase 2.5 Review Queue
    review_queue = []  # List of job_ids waiting for review
    current_reviewing_job = None  # job_id currently being reviewed
    review_dialog = None  # Unused legacy, kept for compatibility
    
    # Helper: Get all video files from output directory
    def get_video_history():
        """Scan output directory for all created videos."""
        output_base = DESKTOP_APP_DIR / "output"
        videos = []
        
        if not output_base.exists():
            return videos
        
        for project_dir in output_base.iterdir():
            if not project_dir.is_dir():
                continue
            
            for video_file in project_dir.glob("*_final.mp4"):
                videos.append({
                    "name": project_dir.name,
                    "path": str(video_file),
                    "size": video_file.stat().st_size,
                    "created": video_file.stat().st_mtime,
                })
            
            if not list(project_dir.glob("*_final.mp4")):
                for video_file in project_dir.glob("*.mp4"):
                    if "_raw" not in video_file.stem:
                        videos.append({
                            "name": project_dir.name,
                            "path": str(video_file),
                            "size": video_file.stat().st_size,
                            "created": video_file.stat().st_mtime,
                        })
        
        videos.sort(key=lambda x: x["created"], reverse=True)
        return videos
    
    def open_video_file(video_path: str):
        """Open video file with default system player."""
        try:
            if platform.system() == "Windows":
                os.startfile(video_path)
            elif platform.system() == "Darwin":
                subprocess.run(["open", video_path])
            else:
                subprocess.run(["xdg-open", video_path])
        except Exception as e:
            logger.error(f"Failed to open video: {e}")
    
    # UI Components
    task_input = ft.TextField(
        label="Mô tả nhiệm vụ",
        hint_text="Nhập nhiệm vụ (VD: Vào google.com và tìm kiếm Python)",
        multiline=True,
        min_lines=3,
        max_lines=5,
        expand=True,
        bgcolor=ft.Colors.WHITE,
        border_color=ft.Colors.BLUE_200,
        focused_border_color=ft.Colors.BLUE_600,
        border_radius=8,
        text_size=13,
    )
    
    video_name_input = ft.TextField(
        label="Tên video",
        hint_text="demo",
        value="demo",
        expand=True,
        bgcolor=ft.Colors.WHITE,
        border_color=ft.Colors.BLUE_200,
        focused_border_color=ft.Colors.BLUE_600,
        border_radius=8,
        text_size=13,
    )
    
    cdp_port_dropdown = ft.Dropdown(
        label="CDP Port",
        value="9222",
        width=140,
        bgcolor=ft.Colors.WHITE,
        border_color=ft.Colors.BLUE_200,
        focused_border_color=ft.Colors.BLUE_600,
        border_radius=8,
        text_size=13,
        options=[
            ft.dropdown.Option("9222", "9222"),
            ft.dropdown.Option("9223", "9223"),
            ft.dropdown.Option("9224", "9224"),
            ft.dropdown.Option("9225", "9225"),
        ],
    )
    

    
    enable_tts_checkbox = ft.Checkbox(
        label="Bật TTS",
        value=True,
        fill_color=ft.Colors.BLUE_600,
    )
    
    tts_engine_dropdown = ft.Dropdown(
        label="TTS Engine",
        value="edge",
        expand=True,
        bgcolor=ft.Colors.WHITE,
        border_color=ft.Colors.BLUE_200,
        focused_border_color=ft.Colors.BLUE_600,
        border_radius=8,
        text_size=13,
        options=[
            ft.dropdown.Option("edge", "Edge TTS"),
            ft.dropdown.Option("fpt", "FPT AI"),
        ]
    )
    
    tts_voice_dropdown = ft.Dropdown(
        label="Giọng đọc",
        value="vi-VN-HoaiMyNeural",
        expand=True,
        bgcolor=ft.Colors.WHITE,
        border_color=ft.Colors.BLUE_200,
        focused_border_color=ft.Colors.BLUE_600,
        border_radius=8,
        text_size=13,
        options=[
            ft.dropdown.Option("vi-VN-HoaiMyNeural", "Hoài My (Nữ)"),
            ft.dropdown.Option("vi-VN-NamMinhNeural", "Nam Minh (Nam)"),
            ft.dropdown.Option("en-US-AriaNeural", "Aria (Female)"),
            ft.dropdown.Option("en-US-GuyNeural", "Guy (Male)"),
        ]
    )
    
    jobs_list = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=12,
    )
    
    history_list = ft.Column(
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=12,
    )
    
    def update_jobs_display():
        """Update running jobs display."""
        jobs_list.controls.clear()
        
        if not running_jobs:
            jobs_list.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.HOURGLASS_EMPTY, size=60, color=ft.Colors.GREY_400),
                        ft.Text("Chưa có job nào đang chạy", size=16, color=ft.Colors.GREY_600)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=16),
                    alignment=ft.alignment.Alignment(0, 0),
                    expand=True,
                )
            )
        else:
            for job_id, job_data in running_jobs.items():
                def make_stop_handler(jid):
                    return lambda e: stop_job(jid)
                
                progress_value = job_data.get("progress", 0)
                status_msg = job_data.get("status", "Đang chạy...")
                cdp_port = job_data.get("cdp_port")
                
                # Add queue indicator if in review queue
                if job_id in review_queue and job_id != current_reviewing_job:
                    queue_pos = review_queue.index(job_id) + 1
                    status_indicator = ft.Container(
                        content=ft.Text(
                            f"Hàng đợi: {queue_pos}",
                            size=11,
                            color=ft.Colors.WHITE,
                            weight=ft.FontWeight.BOLD,
                        ),
                        bgcolor=ft.Colors.ORANGE_600,
                        padding=ft.Padding(left=8, right=8, top=4, bottom=4),
                        border_radius=12,
                    )
                elif job_id == current_reviewing_job:
                    status_indicator = ft.Container(
                        content=ft.Text(
                            "Đang review",
                            size=11,
                            color=ft.Colors.WHITE,
                            weight=ft.FontWeight.BOLD,
                        ),
                        bgcolor=ft.Colors.GREEN_600,
                        padding=ft.Padding(left=8, right=8, top=4, bottom=4),
                        border_radius=12,
                    )
                else:
                    status_indicator = None
                
                # CDP port indicator
                if cdp_port:
                    port_indicator = ft.Container(
                        content=ft.Text(
                            f"Port: {cdp_port}",
                            size=10,
                            color=ft.Colors.WHITE,
                        ),
                        bgcolor=ft.Colors.BLUE_700,
                        padding=ft.Padding(left=6, right=6, top=3, bottom=3),
                        border_radius=10,
                    )
                else:
                    port_indicator = None
                
                card_content = [
                    ft.Row([
                        ft.Column([
                            ft.Row([
                                ft.Text(f"Job #{job_id}: {job_data['video_name']}", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                                status_indicator if status_indicator else ft.Container(),
                                port_indicator if port_indicator else ft.Container(),
                            ], spacing=8),
                            ft.Text(job_data['task'][:60] + "..." if len(job_data['task']) > 60 else job_data['task'], size=12, color=ft.Colors.GREY_600),
                        ], spacing=4, expand=True),
                        ft.IconButton(
                            icon=ft.Icons.STOP_CIRCLE,
                            icon_size=32,
                            icon_color=ft.Colors.RED_600,
                            tooltip="Dừng job",
                            on_click=make_stop_handler(job_id)
                        ),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.ProgressBar(
                        value=progress_value,
                        color=ft.Colors.BLUE_600,
                        bgcolor=ft.Colors.BLUE_100,
                        height=6,
                        border_radius=3,
                    ),
                    ft.Text(status_msg, size=12, color=ft.Colors.BLUE_700),
                ]
                
                card = ft.Container(
                    content=ft.Column(card_content, spacing=8),
                    padding=20,
                    bgcolor=ft.Colors.WHITE,
                    border_radius=12,
                    border=ft.Border.all(1, ft.Colors.BLUE_300),
                )
                jobs_list.controls.append(card)
        
        page.update()
    
    def stop_job(job_id: int):
        """Stop a running job immediately."""
        nonlocal current_reviewing_job
        
        if job_id in running_jobs:
            job_data = running_jobs[job_id]
            
            # Signal cancellation first (threading.Event, immediately visible to all threads)
            if "cancel_event" in job_data:
                job_data["cancel_event"].set()
            
            # Cancel the async task
            if "task_handle" in job_data:
                job_data["task_handle"].cancel()
            
            # If this job is being reviewed, close review panel and move to next
            if current_reviewing_job == job_id:
                _restore_main_area()
                current_reviewing_job = None
                if job_id in review_queue:
                    review_queue.remove(job_id)
            
            # If this job is in review queue, remove it
            if job_id in review_queue:
                review_queue.remove(job_id)
            
            # Resume review event if exists (to unblock pipeline)
            if "review_event" in job_data:
                job_data["review_event"].set()
            
            # Mark as cancelled (run_job's except handler will clean up)
            job_data["status"] = "Dang huy..."
            job_data["progress"] = 0
            update_jobs_display()
            
            logger.info(f"Job #{job_id} stop requested")
    
    def load_history_tab():
        """Load video history into history tab."""
        history_list.controls.clear()
        videos = get_video_history()
        
        if not videos:
            history_list.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.HISTORY, size=60, color=ft.Colors.GREY_400),
                        ft.Text("Chưa có video nào", size=16, color=ft.Colors.GREY_600)
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=16),
                    alignment=ft.alignment.Alignment(0, 0),
                    expand=True,
                )
            )
        else:
            for video in videos:
                created_time = datetime.fromtimestamp(video["created"]).strftime("%Y-%m-%d %H:%M")
                size_mb = video["size"] / (1024 * 1024)
                
                def make_play_handler(path):
                    return lambda e: open_video_file(path)
                
                def make_folder_handler(path):
                    return lambda e: open_video_file(str(Path(path).parent))
                
                card = ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.VIDEO_FILE, size=40, color=ft.Colors.BLUE_600),
                        ft.Column([
                            ft.Text(video["name"], size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                            ft.Text(f"{created_time} • {size_mb:.1f} MB", size=12, color=ft.Colors.GREY_600),
                        ], spacing=4, expand=True),
                        ft.IconButton(
                            icon=ft.Icons.PLAY_CIRCLE_OUTLINE,
                            icon_size=32,
                            icon_color=ft.Colors.GREEN_600,
                            tooltip="Phát video",
                            on_click=make_play_handler(video["path"])
                        ),
                        ft.IconButton(
                            icon=ft.Icons.FOLDER_OPEN,
                            icon_size=28,
                            icon_color=ft.Colors.BLUE_600,
                            tooltip="Mở thư mục",
                            on_click=make_folder_handler(video["path"])
                        ),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=20,
                    bgcolor=ft.Colors.WHITE,
                    border_radius=12,
                    border=ft.Border.all(1, ft.Colors.GREY_300),
                )
                history_list.controls.append(card)
        
        page.update()
    
    def _restore_main_area():
        """Restore the main area to show jobs list."""
        try:
            main_area.content = jobs_content
            update_jobs_display()
            logger.info("Review panel closed, jobs view restored")
        except Exception as ex:
            logger.error(f"Error restoring main area: {ex}")

    def show_review_dialog(job_id: int, tts_script: list):
        """Show TTS script review as an inline panel in main_area."""
        nonlocal current_reviewing_job

        logger.info(f"Job #{job_id}: show_review_dialog called with {len(tts_script) if tts_script else 0} segments")

        if not tts_script:
            if job_id in running_jobs and "review_event" in running_jobs[job_id]:
                running_jobs[job_id]["reviewed_script"] = None
                running_jobs[job_id]["review_event"].set()
            return

        if tts_script:
            logger.info(f"Job #{job_id}: First segment text: {tts_script[0].get('text', '')[:50]}...")

        job_info = running_jobs.get(job_id, {})
        video_name = job_info.get("video_name", f"Job {job_id}")

        # -- Build segment cards --
        segment_controls = []
        segments_column = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)

        def _make_delete_handler(target_idx: int):
            def handler(e):
                to_remove = None
                for ctrl in segment_controls:
                    if ctrl["index"] == target_idx:
                        to_remove = ctrl
                        break
                if to_remove:
                    segment_controls.remove(to_remove)
                    if to_remove["container"] in segments_column.controls:
                        segments_column.controls.remove(to_remove["container"])
                for new_i, ctrl in enumerate(segment_controls):
                    ctrl["index"] = new_i
                    badge = ctrl["container"].content.controls[0]
                    badge.content.value = str(new_i + 1)
                page.update()
            return handler

        def _build_segment_card(idx: int, text: str):
            text_field = ft.TextField(
                value=text,
                multiline=True,
                min_lines=2,
                max_lines=5,
                expand=True,
                bgcolor=ft.Colors.WHITE,
                border_color=ft.Colors.with_opacity(0.35, ft.Colors.BLUE_400),
                focused_border_color=ft.Colors.BLUE_600,
                border_radius=10,
                text_size=13,
                content_padding=ft.Padding(left=14, right=14, top=12, bottom=12),
                cursor_color=ft.Colors.BLUE_700,
            )
            number_badge = ft.Container(
                content=ft.Text(
                    str(idx + 1), size=12, weight=ft.FontWeight.BOLD,
                    color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER,
                ),
                width=28, height=28, border_radius=14,
                bgcolor=ft.Colors.BLUE_600,
                alignment=ft.alignment.Alignment(0, 0),
            )
            delete_btn = ft.IconButton(
                icon=ft.Icons.CLOSE_ROUNDED, icon_size=18,
                icon_color=ft.Colors.RED_400, tooltip="Xóa segment",
                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                on_click=_make_delete_handler(idx),
            )
            card = ft.Container(
                content=ft.Row(
                    [number_badge, text_field, delete_btn],
                    spacing=12, vertical_alignment=ft.CrossAxisAlignment.START,
                ),
                padding=ft.Padding(left=14, right=10, top=12, bottom=12),
                border_radius=12,
                bgcolor=ft.Colors.with_opacity(0.04, ft.Colors.BLUE_600),
                border=ft.Border.all(1, ft.Colors.with_opacity(0.12, ft.Colors.BLUE_400)),
            )
            segment_controls.append({
                "index": idx, "text_field": text_field, "container": card,
            })
            return card

        for idx, segment in enumerate(tts_script):
            card = _build_segment_card(idx, segment.get("text", ""))
            segments_column.controls.append(card)

        logger.info(f"Job #{job_id}: Created {len(segment_controls)} segment cards")

        def on_add_segment(e):
            new_idx = len(segment_controls)
            card = _build_segment_card(new_idx, "")
            segments_column.controls.append(card)
            page.update()

        def on_ok_click(e):
            nonlocal current_reviewing_job
            edited_script = []
            for ctrl in segment_controls:
                text = ctrl["text_field"].value.strip()
                if text:
                    edited_script.append({
                        "text": text,
                        "narration_index": ctrl["index"],
                    })
            if job_id in running_jobs:
                running_jobs[job_id]["reviewed_script"] = edited_script
                running_jobs[job_id]["status"] = "Đang xử lý tiếp video, vui lòng đợi..."
            current_reviewing_job = None
            if job_id in review_queue:
                review_queue.remove(job_id)
            _restore_main_area()
            # Resume pipeline AFTER UI is restored
            if job_id in running_jobs and "review_event" in running_jobs[job_id]:
                running_jobs[job_id]["review_event"].set()
            logger.info(f"Job #{job_id}: Review completed, {len(edited_script)} segments")

        def on_cancel_click(e):
            nonlocal current_reviewing_job
            if job_id in running_jobs:
                running_jobs[job_id]["reviewed_script"] = None
            current_reviewing_job = None
            if job_id in review_queue:
                review_queue.remove(job_id)
            _restore_main_area()
            # Resume pipeline AFTER UI is restored
            if job_id in running_jobs and "review_event" in running_jobs[job_id]:
                running_jobs[job_id]["review_event"].set()
            logger.info(f"Job #{job_id}: Review cancelled, using original script")

        # -- Assemble review panel --
        header = ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Icon(ft.Icons.RECORD_VOICE_OVER_ROUNDED, size=22, color=ft.Colors.WHITE),
                        width=40, height=40, border_radius=12,
                        bgcolor=ft.Colors.BLUE_600,
                        alignment=ft.alignment.Alignment(0, 0),
                    ),
                    ft.Column([
                        ft.Text("Review TTS Script", size=18, weight=ft.FontWeight.W_700, color=ft.Colors.BLUE_900),
                        ft.Text(f"Job #{job_id}  |  {video_name}  |  {len(tts_script)} segments", size=12, color=ft.Colors.GREY_600),
                    ], spacing=2),
                ],
                spacing=14, vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(left=24, right=24, top=20, bottom=16),
            bgcolor=ft.Colors.with_opacity(0.06, ft.Colors.BLUE_600),
            border_radius=ft.BorderRadius(top_left=16, top_right=16, bottom_left=0, bottom_right=0),
        )

        info_row = ft.Container(
            content=ft.Row([
                ft.Icon(ft.Icons.INFO_OUTLINE_ROUNDED, size=16, color=ft.Colors.BLUE_400),
                ft.Text("Chỉnh sửa nội dung thuyết minh, sau đó nhấn Xác nhận để tiếp tục.",
                        size=12, color=ft.Colors.GREY_600, italic=True),
            ], spacing=8),
            padding=ft.Padding(left=24, right=24, top=12, bottom=8),
        )

        action_bar = ft.Container(
            content=ft.Row(
                [
                    ft.TextButton(
                        "Thêm segment mới",
                        icon=ft.Icons.ADD_CIRCLE_OUTLINE_ROUNDED,
                        style=ft.ButtonStyle(
                            color=ft.Colors.BLUE_600,
                            shape=ft.RoundedRectangleBorder(radius=10),
                            padding=ft.Padding(left=14, right=18, top=10, bottom=10),
                        ),
                        on_click=on_add_segment,
                    ),
                    ft.Container(expand=True),
                    ft.TextButton(
                        "Hủy bỏ",
                        icon=ft.Icons.UNDO_ROUNDED,
                        style=ft.ButtonStyle(
                            color=ft.Colors.GREY_600,
                            shape=ft.RoundedRectangleBorder(radius=10),
                            padding=ft.Padding(left=14, right=18, top=10, bottom=10),
                        ),
                        on_click=on_cancel_click,
                    ),
                    ft.FilledButton(
                        "Xác nhận",
                        icon=ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED,
                        style=ft.ButtonStyle(
                            bgcolor=ft.Colors.BLUE_600,
                            color=ft.Colors.WHITE,
                            shape=ft.RoundedRectangleBorder(radius=10),
                            padding=ft.Padding(left=18, right=22, top=12, bottom=12),
                        ),
                        on_click=on_ok_click,
                    ),
                ],
                alignment=ft.MainAxisAlignment.END,
                spacing=10,
            ),
            padding=ft.Padding(left=24, right=24, top=12, bottom=18),
            bgcolor=ft.Colors.with_opacity(0.03, ft.Colors.GREY_600),
            border_radius=ft.BorderRadius(top_left=0, top_right=0, bottom_left=16, bottom_right=16),
            border=ft.Border(top=ft.BorderSide(1, ft.Colors.with_opacity(0.1, ft.Colors.GREY_500))),
        )

        review_panel = ft.Container(
            content=ft.Column(
                [header, info_row, segments_column, action_bar],
                spacing=0, expand=True,
            ),
            bgcolor=ft.Colors.WHITE,
            border_radius=16,
            border=ft.Border.all(1, ft.Colors.BLUE_200),
            expand=True,
            padding=0,
        )

        review_content = ft.Column([
            review_panel,
        ], spacing=0, expand=True)

        # Swap main_area content to show review panel
        main_area.content = review_content
        current_reviewing_job = job_id
        page.update()

        logger.info(f"Job #{job_id}: Review panel shown with {len(tts_script)} segments")
    
    async def run_job(job_id: int, task: str, video_name: str, cdp_port: int, enable_tts: bool, tts_voice: str, tts_engine: str):
        """Run pipeline in background thread."""
        nonlocal current_reviewing_job
        
        cancel_event = threading.Event()
        review_event = asyncio.Event()
        
        running_jobs[job_id]["cancel_event"] = cancel_event
        running_jobs[job_id]["review_event"] = review_event
        
        # Check if Chrome is running on selected port, launch if not
        if not check_chrome_running(cdp_port):
            logger.info(f"Job #{job_id}: Starting Chrome on port {cdp_port}")
            try:
                launch_chrome_with_cdp(cdp_port)
                await asyncio.sleep(3)
                if not check_chrome_running(cdp_port):
                    logger.error(f"Job #{job_id}: Chrome launched but not responding on port {cdp_port}")
                    raise Exception(f"Chrome not responding on port {cdp_port}")
            except Exception as e:
                logger.error(f"Job #{job_id}: Failed to start Chrome: {e}")
                raise
        else:
            logger.info(f"Job #{job_id}: Reusing existing Chrome on port {cdp_port}")
        
        job_cdp_url = f"http://localhost:{cdp_port}"
        running_jobs[job_id]["cdp_port"] = cdp_port
        running_jobs[job_id]["cdp_url"] = job_cdp_url
        
        logger.info(f"Job #{job_id}: Using CDP port {cdp_port}, URL: {job_cdp_url}")
        
        try:
            async def progress_callback(phase: float, message: str, data=None):
                if cancel_event.is_set():
                    raise asyncio.CancelledError("Job cancelled by user")
                
                # Phase 2.5: Review TTS Script
                if phase == 2.5 and data:
                    # Add to review queue
                    if job_id not in review_queue:
                        review_queue.append(job_id)
                    
                    # Save tts_script to job data
                    running_jobs[job_id]["tts_script"] = data
                    
                    # Calculate queue position
                    queue_position = review_queue.index(job_id) + 1 if job_id in review_queue else 0
                    
                    # Update status
                    if current_reviewing_job is None or current_reviewing_job == job_id:
                        running_jobs[job_id]["status"] = "Đang chờ review..."
                    else:
                        running_jobs[job_id]["status"] = f"Đang chờ review (vị trí {queue_position} trong hàng đợi)"
                    
                    running_jobs[job_id]["progress"] = phase / 6
                    update_jobs_display()
                    
                    # Wait for turn in queue
                    while current_reviewing_job is not None and current_reviewing_job != job_id:
                        if cancel_event.is_set():
                            raise asyncio.CancelledError("Job cancelled by user")
                        await asyncio.sleep(0.5)
                    
                    # Our turn - show review dialog
                    running_jobs[job_id]["status"] = "Đang review..."
                    update_jobs_display()
                    
                    show_review_dialog(job_id, data)
                    
                    # Wait for user to complete review
                    await review_event.wait()
                    
                    # Get reviewed script
                    reviewed_script = running_jobs[job_id].get("reviewed_script")
                    
                    # Clear review event for potential reuse
                    review_event.clear()
                    
                    logger.info(f"Job #{job_id}: Phase 2.5 completed")
                    
                    return reviewed_script
                
                # Normal progress update
                if job_id in running_jobs:
                    running_jobs[job_id]["progress"] = phase / 6
                    running_jobs[job_id]["status"] = message
                    update_jobs_display()
                
                return None
            
            video_path = await run_pipeline_v3(
                task=task,
                video_name=video_name,
                cdp_url=job_cdp_url,
                enable_tts=enable_tts,
                tts_voice=tts_voice,
                tts_engine=tts_engine,
                padding_ms=300,
                enable_review=False,
                progress_callback=progress_callback,
                cancel_event=cancel_event,
            )
            
            if job_id in running_jobs:
                if video_path and Path(video_path).exists():
                    running_jobs[job_id]["status"] = "Hoàn thành!"
                    running_jobs[job_id]["progress"] = 1.0
                    running_jobs[job_id]["video_path"] = str(video_path)
                else:
                    running_jobs[job_id]["status"] = "Lỗi: Không tạo được video"
                    running_jobs[job_id]["progress"] = 0
                
                update_jobs_display()
                
                await asyncio.sleep(3)
                if job_id in running_jobs:
                    del running_jobs[job_id]
                    update_jobs_display()
        
        except asyncio.CancelledError:
            logger.info(f"Job #{job_id} cancelled")
            if job_id in running_jobs:
                del running_jobs[job_id]
                update_jobs_display()
        
        except Exception as ex:
            logger.exception(f"Job #{job_id} failed")
            if job_id in running_jobs:
                running_jobs[job_id]["status"] = f"Lỗi: {str(ex)[:50]}"
                running_jobs[job_id]["progress"] = 0
                update_jobs_display()
                
                await asyncio.sleep(5)
                if job_id in running_jobs:
                    del running_jobs[job_id]
                    update_jobs_display()
        
        finally:
            pass
    
    async def start_pipeline_click(e):
        nonlocal job_counter
        
        task = task_input.value
        video_name = video_name_input.value
        cdp_port = int(cdp_port_dropdown.value)
        
        if not task or not video_name:
            page.snack_bar = ft.SnackBar(
                content=ft.Text("Vui lòng điền đầy đủ thông tin!", color=ft.Colors.WHITE),
                bgcolor=ft.Colors.RED_600,
            )
            page.snack_bar.open = True
            page.update()
            return
        
        job_counter += 1
        job_id = job_counter
        
        running_jobs[job_id] = {
            "task": task,
            "video_name": video_name,
            "progress": 0,
            "status": "Đang khởi động...",
            "started": datetime.now(),
        }
        
        task_handle = asyncio.create_task(
            run_job(
                job_id,
                task,
                video_name,
                cdp_port,
                enable_tts_checkbox.value,
                tts_voice_dropdown.value,
                tts_engine_dropdown.value
            )
        )
        
        running_jobs[job_id]["task_handle"] = task_handle
        update_jobs_display()
        
        page.snack_bar = ft.SnackBar(
            content=ft.Text(f"Job #{job_id} đã bắt đầu!", color=ft.Colors.WHITE),
            bgcolor=ft.Colors.GREEN_600,
        )
        page.snack_bar.open = True
        page.update()
    
    run_button = ft.FilledButton(
        "Tạo video mới",
        icon=ft.Icons.ADD_CIRCLE,
        on_click=lambda e: asyncio.create_task(start_pipeline_click(e)),
        height=48,
        expand=True,
    )
    
    # Sidebar: Configuration (left)
    sidebar = ft.Container(
        content=ft.Container(
            content=ft.Column([
                ft.Text("Cấu hình video", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                task_input,
                video_name_input,
                ft.Container(expand=True, content=ft.Divider(height=1, color=ft.Colors.GREY_200)),
                ft.Text("Cài đặt Chrome", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800),
                cdp_port_dropdown,
                ft.Container(expand=True, content=ft.Divider(height=1, color=ft.Colors.GREY_200)),
                ft.Text("Cài đặt TTS", size=13, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800),
                enable_tts_checkbox,
                ft.Row([tts_engine_dropdown, tts_voice_dropdown], spacing=10),
                ft.Container(expand=True),
                run_button,
            ], spacing=10, scroll=ft.ScrollMode.AUTO, expand=True),
            bgcolor=ft.Colors.WHITE,
            border_radius=14,
            padding=20,
            border=ft.Border.all(1, ft.Colors.GREY_200),
            expand=True,
        ),
        width=360,
        padding=ft.Padding(left=14, right=6, top=10, bottom=10),
        bgcolor=ft.Colors.GREY_50,
        expand=True,
    )
    
    # Main area: Running jobs
    main_area = ft.Container(
        content=ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.Icons.WORK_OUTLINE, size=26, color=ft.Colors.BLUE_700),
                        ft.Text("Jobs đang chạy", size=18, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                    ], spacing=10),
                    padding=ft.Padding.only(bottom=10),
                ),
                ft.Container(
                    content=jobs_list,
                    expand=True,
                ),
            ], spacing=0, expand=True),
            bgcolor=ft.Colors.WHITE,
            border_radius=14,
            padding=20,
            border=ft.Border.all(1, ft.Colors.GREY_200),
            expand=True,
        ),
        padding=ft.Padding(left=6, right=14, top=10, bottom=10),
        expand=True,
    )
    # Persistent reference to the jobs content for restore after review
    jobs_content = main_area.content
    
    # Tab contents
    create_tab_content = ft.Container(
        content=ft.Row([
            sidebar,
            main_area,
        ], spacing=0, expand=True, vertical_alignment=ft.CrossAxisAlignment.STRETCH),
        expand=True,
    )
    
    history_tab_content = ft.Container(
        content=ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.Container(
                        content=ft.Icon(ft.Icons.HISTORY, size=28, color=ft.Colors.BLUE_600),
                        bgcolor=ft.Colors.BLUE_50,
                        border_radius=50,
                        padding=10,
                    ),
                    ft.Text("Lịch sử video", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                    ft.Container(expand=True),
                    ft.IconButton(
                        icon=ft.Icons.REFRESH,
                        icon_size=24,
                        icon_color=ft.Colors.BLUE_600,
                        tooltip="Làm mới",
                        on_click=lambda e: load_history_tab(),
                        bgcolor=ft.Colors.BLUE_50,
                    ),
                ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                padding=ft.Padding.only(bottom=20),
            ),
            ft.Container(
                content=history_list,
                expand=True,
            ),
        ], spacing=0, expand=True),
        padding=24,
        expand=True,
    )
    
    # Tab navigation
    tab_create_btn = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.ADD_CIRCLE_OUTLINE, size=20),
            ft.Text("Tạo video", size=14, weight=ft.FontWeight.BOLD),
        ], spacing=8),
        padding=ft.Padding(left=18, right=18, top=10, bottom=10),
        border_radius=10,
    )
    
    tab_history_btn = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.HISTORY, size=20),
            ft.Text("Lịch sử", size=14, weight=ft.FontWeight.BOLD),
        ], spacing=8),
        padding=ft.Padding(left=18, right=18, top=10, bottom=10),
        border_radius=10,
    )
    
    tab_bar = ft.Container(
        content=ft.Row([
            tab_create_btn,
            tab_history_btn,
        ], spacing=8),
        padding=ft.Padding(left=14, right=14, top=8, bottom=8),
        bgcolor=ft.Colors.WHITE,
    )
    
    content_container = ft.Container(
        content=create_tab_content,
        expand=True,
    )
    
    def switch_tab(index: int):
        """Switch between tabs."""
        nonlocal current_tab
        current_tab = index
        
        if index == 0:
            tab_create_btn.bgcolor = ft.Colors.BLUE_600
            tab_create_btn.content.controls[0].color = ft.Colors.WHITE
            tab_create_btn.content.controls[1].color = ft.Colors.WHITE
            tab_history_btn.bgcolor = ft.Colors.TRANSPARENT
            tab_history_btn.content.controls[0].color = ft.Colors.GREY_600
            tab_history_btn.content.controls[1].color = ft.Colors.GREY_600
            content_container.content = create_tab_content
            update_jobs_display()
        else:
            tab_create_btn.bgcolor = ft.Colors.TRANSPARENT
            tab_create_btn.content.controls[0].color = ft.Colors.GREY_600
            tab_create_btn.content.controls[1].color = ft.Colors.GREY_600
            tab_history_btn.bgcolor = ft.Colors.BLUE_600
            tab_history_btn.content.controls[0].color = ft.Colors.WHITE
            tab_history_btn.content.controls[1].color = ft.Colors.WHITE
            content_container.content = history_tab_content
            load_history_tab()
        
        page.update()
    
    tab_create_btn.on_click = lambda e: switch_tab(0)
    tab_history_btn.on_click = lambda e: switch_tab(1)
    
    main_layout = ft.Column([
        tab_bar,
        content_container,
    ], spacing=0, expand=True)
    
    # Wrap in a fixed-size container to maintain pure proportions
    # Subtracting some height for the window title bar if needed, 1280x720 was original window
    BASE_WIDTH = 1280
    BASE_HEIGHT = 680 
    
    app_container = ft.Container(
        content=main_layout,
        width=BASE_WIDTH,
        height=BASE_HEIGHT,
        bgcolor=ft.Colors.GREY_50,
    )
    
    # Center wrapper that expands to fill the real window
    center_wrapper = ft.Container(
        content=app_container,
        alignment=ft.alignment.Alignment(0, 0),
        expand=True,
        bgcolor=ft.Colors.GREY_50,
    )

    def on_resize(e):
        current_width = page.width
        current_height = page.height
        
        if current_width == 0 or current_height == 0:
            return
            
        # Calculate scale prioritizing keeping the entire UI visible
        scale = min(current_width / BASE_WIDTH, current_height / BASE_HEIGHT)
        
        # Apply scaling via transform
        app_container.scale = scale
        app_container.update()

    page.on_resize = on_resize
    page.add(center_wrapper)
    
    # Initial manual trigger
    on_resize(None)
    
    switch_tab(0)


if __name__ == "__main__":
    ft.run(main)
