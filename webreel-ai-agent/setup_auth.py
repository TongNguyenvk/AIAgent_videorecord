import os
from playwright.sync_api import sync_playwright

def setup_auth(domain="https://google.com"):
    print(f"\n=============================================")
    print(f"TRINH DUYET DANG NHAP")
    print(f"=============================================")
    print(f"1. Mot cua so trinh duyet Chrome se hien len.")
    print(f"2. Hay dang nhap vao trang web ban can dung.")
    print(f"3. SAU KHI DANG NHAP XONG VA VAO DUOC TRANG CHINH, HAY TU TAY TAT (CLOSE) CUA SO TRINH DUYET DO.")
    print(f"Du lieu dang nhap se TU DONG DUOC LUU khi ban tat cua so.\n")
    
    # Đảm bảo thư mục output tồn tại
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(output_dir, exist_ok=True)
    profile_dir = os.path.join(output_dir, "browser_profile")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        # Lấy tab mặc định tạo sẵn
        page = context.pages[0] if context.pages else context.new_page()
        
        # Bật chế độ Tàng Hình (Stealth Mode)
        try:
            from playwright_stealth import stealth_sync
            stealth_sync(page)
        except ImportError:
            print("Chua cai playwright-stealth. Chay: pip install playwright-stealth")
            
        page.goto(domain)
        
        # Đợi cho tới khi user TẮT cửa sổ/trình duyệt
        try:
            page.wait_for_event("close", timeout=0)  # timeout=0 nghĩa là đợi vô hạn
        except Exception:
            pass # Bỏ qua lỗi nếu browser bị tắt mạnh tay
            
        print(f"\nDa luu TOAN BO Chrome Profile (History, LocalStorage, Cookies) tai:")
        print(f"{profile_dir}\n")
        
        try:
            context.close()
        except:
            pass

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://google.com"
    setup_auth(url)
