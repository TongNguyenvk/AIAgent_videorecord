# Auth + noVNC Walkthrough

## Architecture

```
User's Browser (http://vps-ip:6080/vnc.html)
    |
    v (WebSocket)
websockify (:6080) -> x11vnc (:5900) -> Xvfb (:99)
                                           |
                                    Chrome (headed, --user-data-dir)
                                           |
                                    web_worker.py (pipeline)
```

## Files Changed

### New Files
| File | Purpose |
|------|---------|
| [docker-entrypoint.sh](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/scripts/docker-entrypoint.sh) | Starts Xvfb + x11vnc + websockify, then runs worker |
| [harvest_auth.py](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/harvest_auth.py) | Backup: Windows-side cookie export script |

### Modified Files
| File | Change |
|------|--------|
| [Dockerfile.backend](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/Dockerfile.backend) | Added `x11vnc novnc websockify`, copy entrypoint |
| [docker-compose.prod.yml](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/docker-compose.prod.yml) | Entrypoint, port 6080, DISPLAY=:99 |
| [web_worker.py](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/worker/web_worker.py) | Enabled `--user-data-dir`, AUTH_STATE_PATH |
| [pipeline.py](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/desktop_app/pipeline.py) | `auth_state_path` param in phase1_scout + run_pipeline_v3 |
| [.env.example](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/.env.example) | AUTH_STATE_PATH config |

## How to Use

```bash
# 1. Build + start
docker compose -f docker-compose.prod.yml up -d --build web-worker

# 2. Open noVNC in browser
#    http://<vps-ip>:6080/vnc.html

# 3. In noVNC: navigate Chrome to https://lms.tvu.edu.vn/
#    Log in with Microsoft SSO manually

# 4. Done! Session saved in chrome_profile volume
#    All future pipeline jobs use the same logged-in Chrome

# 5. (Optional) Close port 6080 in firewall after login
```

> [!IMPORTANT]
> **Luu y `lms_auth.json` mount:** Neu ban chua co file `lms_auth.json`, hay tao file rong truoc khi `docker compose up`:
> ```bash
> echo "{}" > lms_auth.json
> ```
> Hoac xoa dong mount `lms_auth.json` trong docker-compose.prod.yml neu khong can Auth State JSON.

## Security Notes
- noVNC **khong co password** (nopw). Chi mo port 6080 khi can login, sau do dong lai
- Chrome profile persist qua volume mount [chrome_profile/](file:///f:/==HK1-2526==/ThucTap/webreel/webreel-ai-agent/browser-use/browser_use/browser/session.py#434-440)
- Auth state JSON mount read-only (`:ro`), an toan cho multi-worker
