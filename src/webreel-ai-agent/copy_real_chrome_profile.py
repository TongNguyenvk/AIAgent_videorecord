"""
Copy Chrome profile tu Chrome that cua ban sang profile cho automation.

Cach dung:
    1. Dang nhap Google Drive tren Chrome binh thuong cua ban
    2. Chay script nay de copy profile
    3. Script se copy cookies va session sang profile rieng
"""

import os
import shutil
import sqlite3
from pathlib import Path


def find_chrome_profile():
    """Tim Chrome profile mac dinh cua user."""
    possible_paths = [
        Path(os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")),
        Path(os.path.expandvars(r"%APPDATA%\Google\Chrome\User Data")),
    ]
    
    for path in possible_paths:
        if path.exists():
            return path
    
    return None


def copy_chrome_profile():
    print("\n=============================================")
    print("COPY CHROME PROFILE TU CHROME THAT")
    print("=============================================\n")
    
    # Tim Chrome profile that
    source_profile = find_chrome_profile()
    
    if not source_profile:
        print("Khong tim thay Chrome profile!")
        print("Hay dam bao ban da cai dat Chrome va dang nhap Google")
        return False
    
    print(f"Tim thay Chrome profile: {source_profile}")
    
    # Kiem tra Default profile
    default_profile = source_profile / "Default"
    if not default_profile.exists():
        print("\nKhong tim thay Default profile!")
        print("Hay mo Chrome va dang nhap Google Drive truoc")
        return False
    
    # Tao destination profile
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    dest_profile = output_dir / "browser_profile"
    
    # Xoa profile cu neu co
    if dest_profile.exists():
        print(f"\nXoa profile cu: {dest_profile}")
        shutil.rmtree(dest_profile)
    
    dest_profile.mkdir(exist_ok=True)
    dest_default = dest_profile / "Default"
    dest_default.mkdir(exist_ok=True)
    
    print(f"\nDang copy profile...")
    
    # Cac file quan trong can copy
    important_files = [
        "Cookies",
        "Cookies-journal",
        "Local Storage",
        "Session Storage",
        "Preferences",
        "Network",
        "Web Data",
        "Web Data-journal",
    ]
    
    copied_count = 0
    
    for file_name in important_files:
        source_file = default_profile / file_name
        dest_file = dest_default / file_name
        
        if source_file.exists():
            try:
                if source_file.is_dir():
                    shutil.copytree(source_file, dest_file, dirs_exist_ok=True)
                else:
                    shutil.copy2(source_file, dest_file)
                print(f"  Copied: {file_name}")
                copied_count += 1
            except Exception as e:
                print(f"  Loi khi copy {file_name}: {e}")
    
    print(f"\n=============================================")
    print(f"Da copy {copied_count} files/folders")
    print(f"Profile moi: {dest_profile}")
    print("=============================================\n")
    
    # Kiem tra cookies
    cookies_db = dest_default / "Cookies"
    if cookies_db.exists():
        try:
            conn = sqlite3.connect(str(cookies_db))
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM cookies WHERE host_key LIKE '%google%'")
            count = cursor.fetchone()[0]
            conn.close()
            print(f"Tim thay {count} Google cookies trong profile\n")
        except Exception as e:
            print(f"Khong the doc cookies database: {e}\n")
    
    print("CANH BAO QUAN TRONG:")
    print("- Profile nay chi hoat dong tren cung may Windows")
    print("- Cookies co the het han sau vai ngay")
    print("- Neu van bi chan, Google co the da danh dau IP/tai khoan cua ban\n")
    
    print("Bay gio chay test:")
    print("  venv\\Scripts\\python.exe quick_test_session.py")
    
    return True


if __name__ == "__main__":
    copy_chrome_profile()
