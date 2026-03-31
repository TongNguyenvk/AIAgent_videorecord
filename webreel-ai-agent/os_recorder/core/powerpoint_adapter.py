import logging
import win32com.client
import pythoncom
import threading

logger = logging.getLogger(__name__)

from core.base_adapter import BaseAdapter

class PowerPointAdapter(BaseAdapter):
    """
    Engine giao tiếp với PowerPoint qua COM để lấy tọa độ vật lý (Pixel) của văn bản trên Slide,
    giúp Agent nhắm trúng ký tự để bôi đen, click hoặc định dạng.
    """
    def __init__(self):
        super().__init__()
        self._ppt = None
        self.connected = False
        self._thread_id = None
    
    def connect(self) -> bool:
        try:
            pythoncom.CoInitialize()
            self._ppt = win32com.client.GetActiveObject("PowerPoint.Application")
            self.connected = True
            self._thread_id = threading.get_ident()
            logger.info("  [PowerPointAdapter] Đã kết nối thành công vào PowerPoint COM.")
            return True
        except Exception as e:
            try:
                pythoncom.CoInitialize()
                self._ppt = win32com.client.Dispatch("PowerPoint.Application")
                self.connected = True
                self._thread_id = threading.get_ident()
                logger.info("  [PowerPointAdapter] Đã Dispatch thành công PowerPoint COM.")
                return True
            except Exception as e2:
                logger.warning(f"  [PowerPointAdapter] Không thể kết nối PowerPoint COM: {e2}")
                self.connected = False
                return False

    def check_connection(self) -> bool:
        if not self.connected or self._ppt is None:
            return False
        if threading.get_ident() != self._thread_id:
            try:
                pythoncom.CoInitialize()
                self._thread_id = threading.get_ident()
            except Exception:
                pass
        try:
            _ = self._ppt.Name
            return True
        except Exception:
            return self.connect()

    def _find_text_range(self, target_text: str):
        """Duyệt qua các Shape trong Slide hiện hành để tìm TextRange chứa target_text"""
        if not self.check_connection():
            return None
        
        try:
            win = self._ppt.ActiveWindow
            slide = win.View.Slide
            
            for shape in slide.Shapes:
                if shape.HasTextFrame:
                    if shape.TextFrame.HasText:
                        text_range = shape.TextFrame.TextRange
                        found = text_range.Find(FindWhat=target_text)
                        if found:
                            return found, win
            return None
        except Exception as e:
            logger.warning(f"  [PowerPointAdapter] Lỗi tìm text trên Slide: {e}")
            return None

    def get_range_coordinates(self, target_value: str):
        """
        Tìm chuỗi 'target_text' trong PowerPoint và trả về tọa độ kéo thả (Start & End)
        dưới dạng list [(x1, y1), (x2, y2)] bằng PointsToScreenPixels.
        """
        res = self._find_text_range(target_value)
        if not res:
            logger.warning(f"  [PowerPointAdapter] Không tìm thấy chuỗi '{target_value}' trên slide.")
            return None
            
        found_range, win = res
        try:
            # Lấy bounding box của đoạn text tìm được (đơn vị: Point)
            left = found_range.BoundLeft
            top = found_range.BoundTop
            width = found_range.BoundWidth
            height = found_range.BoundHeight
            
            # Chuyển đổi từ Point sang Pixel màn hình
            # PointsToScreenPixelsX/Y yêu cầu giá trị nguyên (int)
            # Tọa độ xuất phát
            start_x = win.PointsToScreenPixelsX(int(left))
            start_y = win.PointsToScreenPixelsY(int(top + height / 2))
            
            # Tọa độ kết thúc (cộng thêm 5px bù dao động DPI)
            end_x = win.PointsToScreenPixelsX(int(left + width)) + 5
            end_y = win.PointsToScreenPixelsY(int(top + height / 2))
            
            logger.info(f"  [PowerPointAdapter] Bat thanh cong chuoi tai ({start_x}, {start_y}) den ({end_x}, {end_y})")
            return [(start_x, start_y), (end_x, end_y)]
        except Exception as e:
            logger.warning(f"  [PowerPointAdapter] Lỗi chuyển đổi tọa độ PowerPoint: {e}")
            return None

    def focus_element(self, target_value: str) -> bool:
        """
        Select ngầm đoạn văn bản mục tiêu trong PowerPoint để hiển thị trạng thái đang chọn.
        """
        res = self._find_text_range(target_value)
        if res:
            found_range, _ = res
            try:
                found_range.Select()
                logger.info(f"  [PowerPointAdapter] Đã Select ngầm chữ '{target_value}' (Visual Update)")
                return True
            except Exception as e:
                logger.warning(f"  [PowerPointAdapter] Lỗi khi Select chữ trong PPT: {e}")
        return False

    def get_coordinates(self, target_value: str):
        coords = self.get_range_coordinates(target_value)
        if coords and len(coords) == 2:
            return (int((coords[0][0] + coords[1][0])/2), coords[0][1])
        return None

    def inject_data(self, target_value: str, data: str) -> bool:
        res = self._find_text_range(target_value)
        if res:
            found_range, _ = res
            try:
                found_range.Text = data
                return True
            except Exception:
                pass
        return False
