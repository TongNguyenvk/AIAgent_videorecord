# 9Router Integration Guide

## ✅ Status: 9Router Running

9Router đã được khởi động thành công tại:

- **Dashboard**: http://localhost:20128
- **API Endpoint**: http://localhost:20128/v1
- **Status**: Running (Terminal ID: 2)

## 📋 Setup Steps Completed

1. ✅ Installed dependencies (`npm install`)
2. ✅ Created `.env` configuration
3. ✅ Started dev server on port 20128
4. ✅ Dashboard accessible

## 🔧 Next Steps

### 1. Configure AI Provider in Dashboard

Mở dashboard tại http://localhost:20128 và:

1. **Login** với credentials:
   - Password: `admin123` (từ `.env`)

2. **Connect FREE Provider** (recommended):
   - Go to **Providers** tab
   - Click **Connect Kiro AI** (FREE unlimited Claude 4.5 + vision)
   - Hoặc **OpenCode Free** (no auth required)
   - Follow OAuth flow

3. **Get API Key**:
   - Go to **Endpoint** tab
   - Copy API key (sẽ dùng trong webreel-ai-agent)

### 2. Test 9Router API

```bash
# Test connection
curl http://localhost:20128/v1/models \
  -H "Authorization: Bearer YOUR_API_KEY"

# Test chat completion (after connecting provider)
curl http://localhost:20128/v1/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "kr/claude-sonnet-4.5",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

### 3. Integrate with webreel-ai-agent

#### Option A: Thay thế Gemini bằng 9Router (recommended)

Edit `webreel-ai-agent/desktop_app/pipeline.py`:

```python
# OLD (line ~150):
from browser_use import ChatGoogle
llm = ChatGoogle(
    model="gemini-3.1-flash-lite-preview",
    api_key=os.getenv("GEMINI_API_KEY"),
)

# NEW:
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(
    base_url="http://localhost:20128/v1",
    api_key=os.getenv("ROUTER_API_KEY"),
    model="kr/claude-sonnet-4.5",  # hoặc model khác có vision
)
```

Add to `webreel-ai-agent/.env`:

```bash
ROUTER_API_KEY=<your-api-key-from-dashboard>
ROUTER_MODEL=kr/claude-sonnet-4.5
```

#### Option B: Giữ Gemini, thêm 9Router làm fallback

```python
# Dual LLM setup
primary_llm = ChatGoogle(...)  # Gemini
fallback_llm = ChatOpenAI(base_url="http://localhost:20128/v1", ...)

try:
    result = await agent.run(llm=primary_llm)
except Exception as e:
    logger.warning(f"Primary LLM failed: {e}, using fallback")
    result = await agent.run(llm=fallback_llm)
```

### 4. Vision Support

Browser-use đã có vision built-in. Chỉ cần đảm bảo model hỗ trợ vision:

**Models có vision qua 9Router:**

- `kr/claude-sonnet-4.5` (Kiro AI - FREE)
- `kr/claude-opus-4.7` (Kiro AI - FREE)
- `gc/gemini-3-flash` (Google Cloud - FREE tier)
- `cx/gpt-4-vision` (Codex - subscription)

Browser-use sẽ tự động gửi screenshot khi cần thiết.

## 🎯 Available FREE Models with Vision

Sau khi connect Kiro AI trong dashboard:

```python
# Claude 4.5 Sonnet (vision + thinking)
model = "kr/claude-sonnet-4.5"

# Claude Opus 4.7 (best quality, vision)
model = "kr/claude-opus-4.7"

# GLM-5 (Chinese model, vision)
model = "kr/glm-5"
```

## 📊 9Router Features

### RTK Token Saver

- Tự động compress tool outputs (git diff, grep, ls...)
- Tiết kiệm 20-40% tokens
- Enabled by default

### Smart Fallback

Tạo combo với auto-fallback:

```
1. kr/claude-sonnet-4.5  (FREE unlimited)
2. gc/gemini-3-flash     (FREE 180K/month)
3. cx/gpt-4-vision       (paid backup)
```

### Usage Tracking

- Real-time token count
- Cost estimation
- Quota monitoring

## 🐛 Troubleshooting

### 9Router không start

```bash
# Check port
netstat -ano | findstr :20128

# Kill process if needed
taskkill /PID <PID> /F

# Restart
cd 9router
npm run dev
```

### API Key không hoạt động

1. Refresh dashboard
2. Go to Endpoint tab
3. Regenerate API key
4. Update `.env` trong webreel-ai-agent

### Provider connection failed

1. Check internet connection
2. Try different provider (Kiro AI, OpenCode Free)
3. Check 9router logs trong terminal

## 📝 Commands

```bash
# Start 9router
cd 9router
npm run dev

# Stop 9router
# Press Ctrl+C in terminal

# View logs
# Check terminal output

# Production build
npm run build
npm run start
```

## 🔗 Resources

- 9Router Dashboard: http://localhost:20128
- 9Router GitHub: https://github.com/decolua/9router
- Browser-use Docs: https://github.com/browser-use/browser-use
- Kiro AI: https://kiro.ai (FREE provider)

## ⚠️ Important Notes

1. **9Router phải chạy trước** khi start webreel-ai-agent pipeline
2. **API Key** phải được set trong `.env` của webreel-ai-agent
3. **Model phải có vision** nếu muốn dùng screenshot analysis
4. **FREE providers** (Kiro, OpenCode) không giới hạn usage

## 🎉 Quick Test

Sau khi setup xong, test integration:

```bash
cd webreel-ai-agent
python -m desktop_app.pipeline "Navigate to google.com and search for 'AI news'" --name test_9router
```

Nếu thành công, bạn sẽ thấy:

- Agent gọi AI qua 9Router (check logs)
- Vision analysis nếu cần (screenshot được gửi)
- Video được tạo thành công

---

**Status**: 9Router running ✅  
**Next**: Configure provider in dashboard → Get API key → Update webreel-ai-agent `.env`
