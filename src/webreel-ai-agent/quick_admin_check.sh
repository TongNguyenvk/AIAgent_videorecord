#!/bin/bash

# Quick Admin Check Script
# Kiểm tra nhanh admin system có hoạt động đúng không

echo "=========================================="
echo "QUICK ADMIN SYSTEM CHECK"
echo "=========================================="

echo ""
echo "1. Checking MongoDB container..."
docker ps --filter "name=mongo" --format "{{.Names}} - {{.Status}}"

echo ""
echo "2. Checking Backend container..."
docker ps --filter "name=api" --format "{{.Names}} - {{.Status}}"

echo ""
echo "3. Testing Backend Health..."
curl -s http://localhost:8000/health | python -m json.tool 2>/dev/null || echo "❌ Backend not responding"

echo ""
echo "4. Counting MongoDB Users..."
docker exec -i webreel-mongodb mongosh -u webreel -p webreel_mongo_2026 --authenticationDatabase admin webreel --quiet --eval "db.users.countDocuments({})" 2>/dev/null || echo "❌ Cannot connect to MongoDB"

echo ""
echo "5. Counting MongoDB Jobs..."
docker exec -i webreel-mongodb mongosh -u webreel -p webreel_mongo_2026 --authenticationDatabase admin webreel --quiet --eval "db.jobs.countDocuments({deleted_at: null})" 2>/dev/null || echo "❌ Cannot connect to MongoDB"

echo ""
echo "6. Checking Admin Users..."
docker exec -i webreel-mongodb mongosh -u webreel -p webreel_mongo_2026 --authenticationDatabase admin webreel --quiet --eval "db.users.countDocuments({role: 'admin'})" 2>/dev/null || echo "❌ Cannot connect to MongoDB"

echo ""
echo "=========================================="
echo "SUMMARY"
echo "=========================================="
echo ""
echo "If all checks pass:"
echo "  ✅ MongoDB is running"
echo "  ✅ Backend is running"
echo "  ✅ Database has users and jobs"
echo ""
echo "Next steps:"
echo "  1. Run: python webreel-ai-agent/test_admin_api.py"
echo "  2. Open: http://localhost:5173"
echo "  3. Login with admin credentials"
echo "  4. Check /admin, /admin/users, /admin/jobs"
echo ""
