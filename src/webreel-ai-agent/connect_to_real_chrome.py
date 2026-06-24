"""
Connect vao Chrome THAT dang chay de su dung session co san.
Day la cach DUY NHAT de vuot Google bot detection.

Cach dung:
    1. Mo Chrome binh thuong, dang nhap Google Drive
    2. Dong Chrome
    3. Mo lai Chrome voi remote debugging:
       "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\selenium\ChromeProfile"
    4. Chay script nay
"""

from playwright.sync_api import sync_playwright
import time


def connect_to_chrome():
    print("\n=============================================")
    print("CONNECT TO REAL CHROME")
    print("=============================================\n")
    
    print("HUONG DAN:")
    print("1. Mo Command Prompt (CMD)")
    print('2. Chay lenh sau (thay doi duong dan neu can):')
    print('   "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222')
    print("3. Dang nhap Google Drive tren Chrome do")
    print("4. Quay lai day va nhan Enter\n")
    
    input("Nhan Enter khi da mo Chrome va dang nhap xong...")
    
    with sync_playwright() as p:
        try:
            print("\nDang ket noi den Chrome...")
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            
            contexts = browser.contexts
            if not contexts:
                print("Khong tim thay context nao!")
                return False
            
            context = contexts[0]
            pages = context.pages
            
            if not pages:
                print("Khong co page nao, dang tao page moi...")
                page = context.new_page()
            else:
                page = pages[0]
            
            print(f"Da ket noi! Hien co {len(pages)} tabs")
            
            # Test vao Google Drive
            print("\nDang test vao Google Drive...")
            page.goto("https://drive.google.com", wait_until="networkidle")
            
            time.sleep(3)
            
            current_url = page.url
            print(f"URL hien tai: {current_url}")
            
            if "accounts.google.com" in current_url:
                print("\n[THAT BAI] Van bi yeu cau dang nhap")
            elif "drive.google.com" in current_url:
                print("\n[THANH CONG] Da vao duoc Drive!")
                print("Session hoat dong tot!")
                
                # Thu lay title
                title = page.title()
                print(f"Page title: {title}")
            
            print("\nNhan Enter de dong ket noi...")
            input()
            
            browser.close()
            
        except Exception as e:
            print(f"\nLoi: {e}")
            print("\nKiem tra lai:")
            print("- Chrome co dang chay voi --remote-debugging-port=9222?")
            print("- Port 9222 co bi chan khong?")
            import traceback
            traceback.print_exc()
            return False
    
    return True


if __name__ == "__main__":
    connect_to_chrome()
