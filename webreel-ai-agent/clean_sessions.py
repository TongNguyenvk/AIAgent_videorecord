"""
Xoa tat ca session cu de bat dau lai tu dau.

Cach dung:
    python clean_sessions.py
"""

import shutil
from pathlib import Path


def clean_all_sessions():
    print("\n=============================================")
    print("XOA TAT CA SESSION CU")
    print("=============================================\n")
    
    output_dir = Path(__file__).parent / "output"
    
    if not output_dir.exists():
        print("Khong co thu muc output, khong can xoa gi")
        return
    
    # Cac thu muc profile can xoa
    profile_dirs = [
        "browser_profile",
        "browser_profile_uc",
        "chrome_profile",
    ]
    
    # Cac file session can xoa
    session_files = [
        "auth_state.json",
        "storage_state.json",
    ]
    
    deleted_count = 0
    
    # Xoa profile directories
    for profile_name in profile_dirs:
        profile_path = output_dir / profile_name
        if profile_path.exists():
            print(f"Dang xoa: {profile_path}")
            try:
                shutil.rmtree(profile_path)
                deleted_count += 1
                print(f"  -> Da xoa")
            except Exception as e:
                print(f"  -> Loi: {e}")
    
    # Xoa session files
    for file_name in session_files:
        file_path = output_dir / file_name
        if file_path.exists():
            print(f"Dang xoa: {file_path}")
            try:
                file_path.unlink()
                deleted_count += 1
                print(f"  -> Da xoa")
            except Exception as e:
                print(f"  -> Loi: {e}")
    
    print(f"\n=============================================")
    if deleted_count > 0:
        print(f"Da xoa {deleted_count} session/profile")
    else:
        print("Khong co session nao de xoa")
    print("=============================================\n")
    
    print("Bay gio chay setup lai:")
    print("  python setup_auth_advanced.py https://drive.google.com")
    print("hoac:")
    print("  python test_undetected.py")


if __name__ == "__main__":
    clean_all_sessions()
