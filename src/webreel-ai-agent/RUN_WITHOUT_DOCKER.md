# Run Backend Without Docker (Recommended for Development)

Docker có vấn đề kết nối tới Chrome CDP trên Windows. Giải pháp đơn giản nhất là chạy backend trực tiếp trên host.

## Prerequisites

1. Python 3.12+
2. Node.js 20+
3. Chrome with remote debugging

## Setup

### 1. Install Python Dependencies

```bash
cd webreel-ai-agent
pip install -r requirements.txt
```

### 2. Install Node Dependencies

```bash
cd ..
pnpm install
```

### 3. Start Chrome

```bash
chrome.exe --remote-debugging-port=9222 --user-data-dir=C:\chrome-debug
```

### 4. Configure Environment

Create `.env` file in `webreel-ai-agent/`:

```env
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
CHROME_CDP_URL=http://localhost:9222
```

### 5. Start Backend

```bash
cd webreel-ai-agent
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Access Application

Open browser: http://localhost:8000

## Advantages

- No Docker networking issues
- Faster development (hot reload)
- Direct access to Chrome CDP
- Easier debugging
- No container overhead

## Docker (For Production Only)

Docker deployment is recommended for production environments where:
- Chrome runs in a separate container (browserless/chrome)
- No manual Chrome session needed
- Automated deployment required

For development on Windows, running directly on host is simpler and more reliable.
