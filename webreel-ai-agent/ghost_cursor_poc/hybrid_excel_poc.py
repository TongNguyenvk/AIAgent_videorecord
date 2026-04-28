import time
import pyautogui
import win32com.client

def run_hybrid_poc():
    print("="*60)
    print("   HYBRID ARCHITECTURE POC: RADAR & ACTOR (GHOST CURSOR)   ")
    print("="*60)
    
    # 1. RADAR LAYER: Sử dụng win32com để query tọa độ
    print("\n[RADAR] Đang kết nối ngầm vào Excel API (COM)...")
    try:
        excel = win32com.client.Dispatch("Excel.Application")
    except Exception as e:
        print(f"Lỗi: Không thể kết nối Excel. Trạm Radar báo lỗi: {e}")
        return

    excel.Visible = True
    
    # Kiểm tra xem có Workbook nào đang mở không, nếu không mở cái mới
    if excel.Workbooks.Count == 0:
        print("[RADAR] Chưa có file nào. Đang gọi file Excel trắng...")
        wb = excel.Workbooks.Add()
    else:
        wb = excel.ActiveWorkbook
        
    ws = wb.ActiveSheet
    
    # Mục tiêu: Đọc tọa độ ô B6
    target_cell = "B6"
    print(f"[RADAR] Đang soi chiếu tọa độ Absolute của ô {target_cell} trên màn hình...")
    
    range_obj = ws.Range(target_cell)
    
    # Công thức quy đổi của Microsoft:
    # Lấy lề Left/Top (Twips) + Chiều ngang của ô chia đôi (để lấy Tâm)
    center_x_points = range_obj.Left + (range_obj.Width / 2)
    center_y_points = range_obj.Top + (range_obj.Height / 2)
    
    # ActiveWindow.PointsToScreenPixelsX nội suy thẳng ra tọa độ Pixel màn hình thật (Bất chấp DPI/Zoom)
    x_pixel = excel.ActiveWindow.PointsToScreenPixelsX(int(center_x_points))
    y_pixel = excel.ActiveWindow.PointsToScreenPixelsY(int(center_y_points))
    
    print(f"[RADAR] Tọa độ vật lý chính xác: Tọa độ X = {x_pixel}, Y = {y_pixel}")
    
    
    # 2. ACTOR LAYER: Dùng PyAutoGUI lướt chuột mượt mà (Ghost Cursor)
    print("\n[ACTOR] Kích hoạt con trỏ chuột biểu diễn (Motion Tweening)...")
    print("   -> Di chuột lướt nhẹ nhàng tới mục tiêu...")
    time.sleep(1) # Chờ 1 nhịp để User xem
    
    # duration=1.2s và tween=easeInOutQuad tạo cảm giác chuột di chuyển cực kỳ người và điện ảnh
    pyautogui.moveTo(x_pixel, y_pixel, duration=1.2, tween=pyautogui.easeInOutQuad)
    
    print("   -> Đã đến tọa độ Radar chỉ định. Cúp cò Click!")
    pyautogui.click()
    
    
    # 3. SAFE INPUT LAYER: Đẩy dữ liệu chống cháy Unikey
    print("\n[BACKEND] Đang tiêm Text tiếng Việt 100% nguyên bản vào lõi COM Excel...")
    time.sleep(0.5)
    
    # Ghi thẳng thuộc tính .Value => Không thông qua bàn phím => Unikey bị mù hoàn toàn
    range_obj.Value = "Báo cáo doanh thu Webreel Agent"
    
    print("   -> Bơm Text thành công!")
    
    
    # 4. CHUYỂN SANG Ô KHÁC
    print("\n[HYBRID] Biểu diễn tính Điểm Trung Bình ở ô D6...")
    time.sleep(1.5)
    
    d6 = ws.Range("D6")
    d6_x = excel.ActiveWindow.PointsToScreenPixelsX(int(d6.Left + d6.Width / 2))
    d6_y = excel.ActiveWindow.PointsToScreenPixelsY(int(d6.Top + d6.Height / 2))
    
    print(f"   [RADAR] Tọa độ D6: X = {d6_x}, Y = {d6_y}")
    pyautogui.moveTo(d6_x, d6_y, duration=0.8, tween=pyautogui.easeInOutQuad)
    pyautogui.click()
    
    print("   [BACKEND] Tiêm Công Thức: '=AVERAGE(A1:A5)'")
    d6.Value = "=AVERAGE(A1:A5)"
    
    print("\n" + "="*60)
    print("   POC GHOST CURSOR ĐÃ HOÀN TẤT XUẤT SẮC!   ")
    print("="*60)

if __name__ == "__main__":
    run_hybrid_poc()
