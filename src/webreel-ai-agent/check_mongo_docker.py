"""
Check MongoDB accounts via Docker exec.

Since MongoDB is not exposed to localhost, we'll use docker exec to run mongosh.
"""

import subprocess
import json

def run_docker_command(cmd):
    """Run docker exec command and return output."""
    full_cmd = ["docker", "exec", "-i", "webreel-mongodb", "mongosh", 
                "-u", "webreel", "-p", "webreel_mongo_2026", 
                "--authenticationDatabase", "admin",
                "webreel", "--quiet", "--eval", cmd]
    
    try:
        result = subprocess.run(full_cmd, capture_output=True, text=True, timeout=10)
        return result.stdout.strip()
    except Exception as e:
        print(f"Error: {e}")
        return None


def main():
    print("=" * 80)
    print("CHECKING MONGODB ACCOUNTS (via Docker)")
    print("=" * 80)
    
    # Count users
    print("\n📊 Counting users...")
    count_cmd = "db.users.countDocuments({})"
    count = run_docker_command(count_cmd)
    print(f"Total users: {count}")
    
    # List all users
    print("\n" + "=" * 80)
    print("ALL USERS:")
    print("=" * 80)
    
    list_cmd = """
    db.users.find({}).forEach(function(user) {
        print(JSON.stringify({
            user_id: user.user_id,
            email: user.email,
            role: user.role,
            tier: user.tier,
            status: user.status,
            created_at: user.created_at
        }));
    });
    """
    
    output = run_docker_command(list_cmd)
    
    if output:
        lines = output.split('\n')
        admin_found = False
        
        for i, line in enumerate(lines, 1):
            if line.strip():
                try:
                    user = json.loads(line)
                    print(f"\n{i}. User ID: {user.get('user_id')}")
                    print(f"   Email: {user.get('email')}")
                    print(f"   Role: {user.get('role', 'user')}")
                    print(f"   Tier: {user.get('tier', 'free')}")
                    print(f"   Status: {user.get('status', 'active')}")
                    
                    if user.get('role') == 'admin':
                        admin_found = True
                except json.JSONDecodeError:
                    continue
        
        # Highlight admin accounts
        print("\n" + "=" * 80)
        print("ADMIN ACCOUNTS:")
        print("=" * 80)
        
        if not admin_found:
            print("⚠️  NO ADMIN ACCOUNTS FOUND!")
            print("\nTo create an admin account:")
            print("1. Run: docker exec -it webreel-mongodb mongosh -u webreel -p webreel_mongo_2026 webreel")
            print("2. Then run:")
            print("""
db.users.insertOne({
    user_id: "admin-001",
    email: "admin@webreel.com",
    password_hash: "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIeWEHaSuu",
    name: "Admin User",
    role: "admin",
    tier: "enterprise",
    status: "active",
    email_verified: true,
    created_at: new Date(),
    quota: {
        videos_per_month: 999999,
        videos_used_this_month: 0,
        reset_date: new Date(new Date().setMonth(new Date().getMonth() + 1))
    }
})
            """)
            print("\nPassword for above hash: admin123")
        else:
            print("\n✅ Admin accounts found!")
            
            # Re-run to show admin details
            admin_cmd = """
            db.users.find({role: "admin"}).forEach(function(user) {
                print(JSON.stringify({
                    email: user.email,
                    user_id: user.user_id,
                    status: user.status,
                    tier: user.tier
                }));
            });
            """
            
            admin_output = run_docker_command(admin_cmd)
            if admin_output:
                for line in admin_output.split('\n'):
                    if line.strip():
                        try:
                            admin = json.loads(line)
                            print(f"\n🔑 Admin: {admin.get('email')}")
                            print(f"   User ID: {admin.get('user_id')}")
                            print(f"   Status: {admin.get('status')}")
                            print(f"   Tier: {admin.get('tier')}")
                        except:
                            continue
    else:
        print("❌ Failed to retrieve users from MongoDB")
    
    print("\n" + "=" * 80)
    print("TEST CREDENTIALS:")
    print("=" * 80)
    print("\nIf you have admin@webreel.com:")
    print("  Email: admin@webreel.com")
    print("  Password: admin123")
    print("\nTest with:")
    print("  python webreel-ai-agent/test_admin_api.py")


if __name__ == "__main__":
    main()
