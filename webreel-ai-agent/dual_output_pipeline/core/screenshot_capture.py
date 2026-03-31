"""
Screenshot Capture Module
Chup anh man hinh tai cac thoi diem thuc thi step
"""
import logging
import pyautogui
from pathlib import Path
from typing import Optional
import time

logger = logging.getLogger(__name__)

class ScreenshotCapture:
    """Chup anh man hinh de tao document"""
    
    def __init__(self, output_dir: Path, target_pid: int = None):
        self.output_dir = output_dir
        # Neu output_dir da la screenshots folder thi dung luon, khong tao subfolder nua
        if output_dir.name == "screenshots":
            self.screenshots_dir = output_dir
        else:
            self.screenshots_dir = output_dir / "screenshots"
        self.screenshots_dir.mkdir(exist_ok=True, parents=True)
        self.target_pid = target_pid
        logger.info(f"  [ScreenshotCapture] Khoi tao: {self.screenshots_dir}")
        if target_pid:
            logger.info(f"  [ScreenshotCapture] Target PID: {target_pid}")
    
    def capture_step(self, step_index: int, delay_ms: int = 100) -> str:
        """
        Chup anh man hinh tai thoi diem thuc thi buoc
        
        Args:
            step_index: So thu tu buoc
            delay_ms: Do tre sau khi chuot di chuyen (de PowerToys kip hien thi)
        
        Returns:
            Duong dan file anh da luu
        """
        time.sleep(delay_ms / 1000)
        
        filename = f"step_{step_index:03d}.png"
        filepath = self.screenshots_dir / filename
        
        try:
            # Neu co target_pid, thu chup chi cua so do
            if self.target_pid:
                screenshot = self._capture_window_by_pid(self.target_pid)
                if screenshot:
                    screenshot.save(filepath)
                    logger.info(f"  [ScreenshotCapture] Da chup cua so (PID={self.target_pid}): {filename}")
                    return str(filepath)
            
            # Fallback: chup toan man hinh
            screenshot = pyautogui.screenshot()
            screenshot.save(filepath)
            logger.info(f"  [ScreenshotCapture] Da chup toan man hinh: {filename}")
            return str(filepath)
        except Exception as e:
            logger.error(f"  [ScreenshotCapture] Loi chup anh: {e}")
            return None
    
    def capture_step_with_highlight(self, step_index: int, step_data: dict, delay_ms: int = 100, max_retries: int = 3) -> str:
        """
        Chup anh voi retry mechanism va highlight click area
        
        Args:
            step_index: So thu tu buoc
            step_data: Du lieu buoc (co x, y, action_type)
            delay_ms: Do tre ban dau
            max_retries: So lan retry toi da
        
        Returns:
            Duong dan file anh da highlight
        """
        for attempt in range(max_retries):
            current_delay = delay_ms + (attempt * 50)
            time.sleep(current_delay / 1000)
            
            filename = f"step_{step_index:03d}.png"
            filepath = self.screenshots_dir / filename
            
            try:
                # Chup anh
                if self.target_pid:
                    screenshot = self._capture_window_by_pid(self.target_pid)
                    if screenshot:
                        screenshot.save(filepath)
                    else:
                        screenshot = pyautogui.screenshot()
                        screenshot.save(filepath)
                else:
                    screenshot = pyautogui.screenshot()
                    screenshot.save(filepath)
                
                # Validate
                if not self._is_valid_screenshot(filepath):
                    logger.warning(f"  [ScreenshotCapture] Invalid screenshot (attempt {attempt+1}), retrying...")
                    continue
                
                # Highlight neu la click/type action
                action_type = step_data.get('action_type', '')
                if action_type in ('click_element', 'type_text', 'double_click', 'right_click'):
                    x = step_data.get('x', 0)
                    y = step_data.get('y', 0)
                    
                    # Convert toa do neu chup window-specific
                    if self.target_pid and x > 0 and y > 0:
                        x, y = self._convert_screen_to_window_coords(x, y)
                    
                    if x > 0 and y > 0:
                        self.highlight_click_area(str(filepath), x, y, radius=40)
                
                logger.info(f"  [ScreenshotCapture] Captured (attempt {attempt+1}): {filename}")
                return str(filepath)
                
            except Exception as e:
                logger.error(f"  [ScreenshotCapture] Error (attempt {attempt+1}): {e}")
        
        # Fallback: tao placeholder
        logger.error(f"  [ScreenshotCapture] Failed after {max_retries} attempts")
        return self.create_placeholder_image(step_index, "Screenshot failed after retries")
    
    def _is_valid_screenshot(self, filepath: str) -> bool:
        """Kiem tra anh co hop le khong"""
        try:
            from PIL import Image
            import numpy as np
            
            img = Image.open(filepath)
            
            # Kiem tra kich thuoc
            if img.width < 100 or img.height < 100:
                return False
            
            # Kiem tra khong phai anh trang/den hoan toan
            img_array = np.array(img)
            mean_color = img_array.mean()
            
            # Neu mean qua gan 0 (den) hoac 255 (trang) -> invalid
            if mean_color < 10 or mean_color > 245:
                return False
            
            return True
        except Exception as e:
            logger.error(f"  [ScreenshotCapture] Error validating: {e}")
            return False
    
    def _convert_screen_to_window_coords(self, screen_x: int, screen_y: int) -> tuple:
        """Convert toa do man hinh sang toa do window"""
        try:
            import win32gui
            
            # Tim window handle
            def callback(hwnd, hwnds):
                import win32process
                _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                if found_pid == self.target_pid and win32gui.IsWindowVisible(hwnd):
                    hwnds.append(hwnd)
                return True
            
            hwnds = []
            win32gui.EnumWindows(callback, hwnds)
            
            if not hwnds:
                return screen_x, screen_y
            
            hwnd = hwnds[0]
            left, top, _, _ = win32gui.GetWindowRect(hwnd)
            
            # Convert
            window_x = screen_x - left
            window_y = screen_y - top
            
            return window_x, window_y
        except Exception as e:
            logger.warning(f"  [ScreenshotCapture] Cannot convert coords: {e}")
            return screen_x, screen_y
    
    def create_placeholder_image(self, step_index: int, error_msg: str = "Screenshot failed") -> str:
        """Tao anh placeholder khi screenshot fail"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            filename = f"step_{step_index:03d}_placeholder.png"
            filepath = self.screenshots_dir / filename
            
            # Tao anh trang
            img = Image.new('RGB', (800, 600), color=(240, 240, 240))
            draw = ImageDraw.Draw(img)
            
            # Ve text
            try:
                font = ImageFont.truetype("arial.ttf", 40)
            except:
                font = ImageFont.load_default()
            
            text = f"Step {step_index}\n{error_msg}"
            
            # Tinh toan vi tri text o giua
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (800 - text_width) // 2
            y = (600 - text_height) // 2
            
            draw.text((x, y), text, fill=(128, 128, 128), font=font)
            
            img.save(filepath)
            logger.info(f"  [ScreenshotCapture] Created placeholder: {filename}")
            
            return str(filepath)
        except Exception as e:
            logger.error(f"  [ScreenshotCapture] Error creating placeholder: {e}")
            return None
    
    def _capture_window_by_pid(self, pid: int):
        """Chup anh chi cua so cua PID cu the"""
        try:
            import win32gui
            import win32ui
            import win32con
            from PIL import Image
            
            # Tim window handle tu PID
            def callback(hwnd, hwnds):
                import win32process
                _, found_pid = win32process.GetWindowThreadProcessId(hwnd)
                if found_pid == pid and win32gui.IsWindowVisible(hwnd):
                    hwnds.append(hwnd)
                return True
            
            hwnds = []
            win32gui.EnumWindows(callback, hwnds)
            
            if not hwnds:
                logger.warning(f"  [ScreenshotCapture] Khong tim thay window cho PID={pid}")
                return None
            
            hwnd = hwnds[0]
            
            # Lay kich thuoc cua so
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
            
            # Chup anh cua so
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)
            
            result = saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)
            
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            
            im = Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1
            )
            
            # Cleanup
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)
            
            return im
            
        except Exception as e:
            logger.warning(f"  [ScreenshotCapture] Loi chup cua so: {e}")
            return None
    
    def capture_region(self, x: int, y: int, width: int, height: int, step_index: int) -> str:
        """Chup mot vung cu the tren man hinh"""
        filename = f"step_{step_index:03d}_region.png"
        filepath = self.screenshots_dir / filename
        
        try:
            screenshot = pyautogui.screenshot(region=(x, y, width, height))
            screenshot.save(filepath)
            logger.info(f"  [ScreenshotCapture] Da chup vung: {filename}")
            return str(filepath)
        except Exception as e:
            logger.error(f"  [ScreenshotCapture] Loi chup vung: {e}")
            return None
    
    def highlight_click_area(self, image_path: str, x: int, y: int, radius: int = 30):
        """Ve vong tron do quanh vi tri click"""
        try:
            import cv2
            import numpy as np
            
            img = cv2.imread(image_path)
            if img is None:
                logger.error(f"  [ScreenshotCapture] Khong doc duoc anh: {image_path}")
                return
            
            cv2.circle(img, (x, y), radius, (0, 0, 255), 3)
            cv2.imwrite(image_path, img)
            logger.info(f"  [ScreenshotCapture] Da highlight click area")
        except Exception as e:
            logger.error(f"  [ScreenshotCapture] Loi highlight: {e}")
