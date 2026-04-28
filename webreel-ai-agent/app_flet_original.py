"""
AI Video Tutor - Desktop App (Flet UI)
Standalone version with multi-threading and job control
"""

import flet as ft
import asyncio
import logging
from pathlib import Path
from pipeline import run_pipeline_v3
from dotenv import load_dotenv
import os
import subprocess
import platform
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

DESKTOP_APP_DIR = Path(__file__).parent
env_path = DESKTOP_APP_DIR / ".env"
if env_path.exists():
    load_dotenv(env_path)


def main(page: ft.Page):
    page.title = "AI Video Tutor"
    page.window.width = 1400
    page.window.height = 900
    page.padding = 0
    page.scroll = ft.ScrollMode.HIDDEN
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = ft.Colors.GREY_50
    
    # State
    running_jobs = {}
    job_counter = 0
    current_tab = 0
    
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
        min_lines=4,
        max_lines=6,
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
    
    cdp_url_input = ft.TextField(
        label="Chrome CDP URL",
        value="http://localhost:9222",
        expand=True,
        bgcolor=ft.Colors.WHITE,
        border_color=ft.Colors.BLUE_200,
        focused_border_color=ft.Colors.BLUE_600,
        border_radius=8,
        text_size=13,
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
                
                card = ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Column([
                                ft.Text(f"Job #{job_id}: {job_data['video_name']}", size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
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
                    ], spacing=8),
                    padding=20,
                    bgcolor=ft.Colors.WHITE,
                    border_radius=12,
                    border=ft.Border.all(1, ft.Colors.BLUE_300),
                )
                jobs_list.controls.append(card)
        
        page.update()
    
    def stop_job(job_id: int):
        """Stop a running job."""
        if job_id in running_jobs:
            job_data = running_jobs[job_id]
            if "task_handle" in job_data:
                job_data["task_handle"].cancel()
            
            if "cancel_event" in job_data:
                job_data["cancel_event"].set()
            
            del running_jobs[job_id]
            update_jobs_display()
            
            logger.info(f"Job #{job_id} stopped by user")
    
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
    
    async def run_job(job_id: int, task: str, video_name: str, cdp_url: str, enable_tts: bool, tts_voice: str, tts_engine: str):
        """Run pipeline in background thread."""
        cancel_event = asyncio.Event()
        running_jobs[job_id]["cancel_event"] = cancel_event
        
        try:
            async def progress_callback(phase: float, message: str, data=None):
                if cancel_event.is_set():
                    raise asyncio.CancelledError("Job cancelled by user")
                
                if job_id in running_jobs:
                    running_jobs[job_id]["progress"] = phase / 6
                    running_jobs[job_id]["status"] = message
                    update_jobs_display()
                
                return None
            
            video_path = await run_pipeline_v3(
                task=task,
                video_name=video_name,
                cdp_url=cdp_url,
                enable_tts=enable_tts,
                tts_voice=tts_voice,
                tts_engine=tts_engine,
                padding_ms=300,
                enable_review=False,
                progress_callback=progress_callback,
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
    
    async def start_pipeline_click(e):
        nonlocal job_counter
        
        task = task_input.value
        video_name = video_name_input.value
        cdp_url = cdp_url_input.value
        
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
                cdp_url,
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
    
    run_button = ft.ElevatedButton(
        "Tạo video mới",
        icon=ft.Icons.ADD_CIRCLE,
        on_click=lambda e: asyncio.create_task(start_pipeline_click(e)),
        height=54,
        bgcolor=ft.Colors.BLUE_600,
        color=ft.Colors.WHITE,
        elevation=2,
        expand=True,
    )
    
    # Sidebar: Configuration (left, narrow)
    sidebar = ft.Container(
        content=ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Column([
                        ft.Container(
                            content=ft.Icon(ft.Icons.SMART_DISPLAY, size=36, color=ft.Colors.BLUE_600),
                            bgcolor=ft.Colors.BLUE_50,
                            border_radius=50,
                            padding=12,
                        ),
                        ft.Text(
                            "Cấu hình video",
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.BLUE_900
                        ),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=12),
                    padding=ft.Padding.only(bottom=24),
                ),
                
                task_input,
                video_name_input,
                cdp_url_input,
                
                ft.Divider(height=1, color=ft.Colors.GREY_200),
                
                ft.Container(
                    content=ft.Column([
                        ft.Text("Cài đặt TTS", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_800),
                        enable_tts_checkbox,
                        tts_engine_dropdown,
                        tts_voice_dropdown,
                    ], spacing=12),
                    padding=ft.Padding.only(top=12, bottom=12),
                ),
                
                ft.Divider(height=1, color=ft.Colors.GREY_200),
                
                ft.Container(
                    content=run_button,
                    padding=ft.Padding.only(top=16),
                ),
            ], spacing=16, scroll=ft.ScrollMode.AUTO),
            bgcolor=ft.Colors.WHITE,
            border_radius=16,
            padding=24,
            border=ft.Border.all(1, ft.Colors.GREY_200),
        ),
        width=380,
        padding=16,
        bgcolor=ft.Colors.GREY_50,
    )
    
    # Main area: Running jobs
    main_area = ft.Container(
        content=ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.WORK_OUTLINE, size=28, color=ft.Colors.BLUE_700),
                    ft.Text("Jobs đang chạy", size=20, weight=ft.FontWeight.BOLD, color=ft.Colors.BLUE_900),
                ], spacing=12),
                padding=ft.Padding.only(bottom=12),
            ),
            ft.Container(
                content=jobs_list,
                expand=True,
            ),
        ], spacing=0, expand=True),
        padding=20,
        expand=True,
    )
    
    # Tab contents
    create_tab_content = ft.Container(
        content=ft.Row([
            sidebar,
            main_area,
        ], spacing=0, expand=True, vertical_alignment=ft.CrossAxisAlignment.START),
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
        padding=ft.Padding(left=20, right=20, top=12, bottom=12),
        border_radius=12,
    )
    
    tab_history_btn = ft.Container(
        content=ft.Row([
            ft.Icon(ft.Icons.HISTORY, size=20),
            ft.Text("Lịch sử", size=14, weight=ft.FontWeight.BOLD),
        ], spacing=8),
        padding=ft.Padding(left=20, right=20, top=12, bottom=12),
        border_radius=12,
    )
    
    tab_bar = ft.Container(
        content=ft.Row([
            tab_create_btn,
            tab_history_btn,
        ], spacing=8),
        padding=16,
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
    
    page.add(main_layout)
    switch_tab(0)


if __name__ == "__main__":
    ft.run(main)
