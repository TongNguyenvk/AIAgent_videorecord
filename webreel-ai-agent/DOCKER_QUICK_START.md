# Docker Quick Start Guide

## Step 1: Start Chrome with Docker Access

Run the provided script:
```bash
start-chrome-docker.bat
```

Or manually:
```bash
# Close existing Chrome
taskkill /F /IM chrome.exe

# Start Chrome with Docker-compatible flags
chrome.exe --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=C:\chrome-debug
```

## Step 2: Verify Chrome CDP

```bash
curl http://localhost:9222/json/version
```

Should return Chrome version info.

## Step 3: Start Backend

```bash
cd webreel-ai-agent
docker-compose -f docker-compose.backend.yml up
```

## Step 4: Access Application

Open browser: http://localhost:8000

## Troubleshooting

### Chrome Connection Failed

If you see "Chrome not available" error:

1. Check Chrome is running:
```bash
curl http://localhost:9222/json/version
```

2. Test from Docker:
```bash
docker exec webreel-backend curl http://host.docker.internal:9222/json/version
```

3. If step 2 fails, Chrome needs `--remote-allow-origins=*` flag

### Container Cannot Connect to Host

On Windows, `host.docker.internal` should work automatically with Docker Desktop.

If not working, check Docker Desktop settings:
- Settings > Resources > Network
- Ensure "Use kernel networking for UDP" is disabled

### Alternative: Use IP Address

Find your host IP:
```bash
ipconfig
```

Update docker-compose.backend.yml:
```yaml
environment:
  - CHROME_CDP_URL=http://YOUR_IP:9222
```

## Production Deployment

For production without manual Chrome session:

1. Use browserless/chrome in Docker
2. Remove manual session requirement
3. Let browser-use create new sessions automatically

See `docker-compose.backend.yml` for Chrome service configuration.
