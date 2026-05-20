"""
Reset password cho admin user hiện có trong database.
"""
import asyncio
from backend.database import Database
from backend.auth import hash_password

async def reset_admin_password():
    """Reset password cho admin@webreel.com"""
    print("🔄 Đang kết nối MongoDB...")
    await Database.connect()
    db = Database.get_db()
    
    if not db:
        print("❌ Không thể kết nối MongoDB!")
        return
    
    # Tìm admin user
    admin = await db.users.find_one({"email": "admin@webreel.com"})
    
    if not admin:
        print("❌ Không tìm thấy admin user với email: admin@webreel.com")
        print("\n💡 Tạo admin mới bằng: python backend/scripts/create_admin.py")
        await Database.disconnect()
        return
    
    print(f"\n✅ Tìm thấy admin user:")
    print(f"   Email: {admin['email']}")
    print(f"   Name: {admin['name']}")
    print(f"   Role: {admin.get('role', 'N/A')}")
    print(f"   Tier: {admin['tier']}")
    
    # Nhập password mới
    print("\n" + "="*50)
    new_password = input("Nhập password mới (hoặc Enter để dùng 'admin123'): ").strip()
    
    if not new_password:
        new_password = "admin123"
        print(f"✅ Sử dụng password mặc định: {new_password}")
    
    # Hash password
    password_hash = hash_password(new_password)
    
    # Update database
    result = await db.users.update_one(
        {"email": "admin@webreel.com"},
        {"$set": {"password_hash": password_hash}}
    )
    
    if result.modified_count > 0:
        print("\n" + "="*50)
        print("✅ Password đã được reset thành công!")
        print("="*50)
        print(f"\n📧 Email: admin@webreel.com")
        print(f"🔑 Password: {new_password}")
        print(f"\n🌐 Login tại: http://localhost:5173/login")
        print("="*50)
    else:
        print("\n⚠️  Không có thay đổi nào được thực hiện")
        print("   (Password có thể đã giống với password hiện tại)")
    
    await Database.disconnect()
    print("\n✅ Hoàn tất!")

if __name__ == "__main__":
    try:
        asyncio.run(reset_admin_password())
    except KeyboardInterrupt:
        print("\n\n❌ Đã hủy bởi người dùng")
    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        import traceback
        traceback.print_exc()
