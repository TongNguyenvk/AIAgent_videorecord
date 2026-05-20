# Product Requirements Document (PRD)

# Docker Security Hardening and Consolidate Entry Point

## 1. Objective

Harden the WebReel container security by consolidating all external network traffic through a single entry point (Nginx reverse proxy in the frontend container), hiding all backend and internal services from direct host-port exposure, and establishing an automated iptables firewall script with Cloudflare IP validation for production deployment.

## 2. Current System Problems

- **Exposed Ports:** Currently, multiple services map ports to the host system directly in `docker-compose.prod.yml`, including `api` (8000), `frontend` (3000), and `session-manager` (6080 for noVNC, 5900 for VNC, 8001 for freeze API). This exposes internal APIs and control panels to network scanners.
- **Access Complexity:** The administrator must maintain SSH tunnels to access the session manager (noVNC) locally or in production because the backend returns `http://localhost:6080` for embedding noVNC in the dashboard.
- **Firewall Lack:** There is no specialized firewall rule for Docker container traffic. Standard host firewalls like UFW are bypassed by Docker's default NAT routing.

## 3. Key Requirements and Features

### 3.1. Single Entry Point Consolidation (Port Isolation)

- Remove the `ports` mapping configuration from the `api` and `session-manager` services in `docker-compose.prod.yml`.
- Keep the `ports` mapping configuration only on the `frontend` container (which runs Nginx).
- In production, the Nginx container will map port `80` (and `443` for SSL) to the host. For local development and testing, it can continue to map `3000:80` or a single configurable port.
- Enable Nginx to act as a gateway routing all external HTTP and WebSocket requests to their respective backend services inside the Docker internal network.

### 3.2. Nginx Reverse Proxy Updates

Update `frontend/nginx.conf` to handle:

- **API Routing:** Route `/api/` traffic to the `api` container on port 8000.
- **noVNC Web Interface:** Route `/novnc/` traffic to the `session-manager` container on port 6080.
- **noVNC WebSocket Upgrade:** Support upgrading HTTP connection to WebSocket protocol on the same `/novnc/` path (forwarding to websockify).
- **Real IP Restoration:** Add Nginx directives (`set_real_ip_from` and `real_ip_header`) to restore the real client IP address from the `CF-Connecting-IP` header sent by Cloudflare, ensuring logs record the correct client source IP.

### 3.3. Relative VNC URL Resolving

- Update `backend/admin_routes.py` (specifically `/admin/novnc-url`) to return a relative URL `/novnc/vnc.html?path=novnc/websockify&autoconnect=true&resize=scale` instead of a hardcoded `localhost:6080` absolute URL.
- This allows the admin dashboard to load the noVNC iframe directly through the same host and port.

### 3.4. Host-Level iptables Firewall Script

Create a bash script `scripts/setup-cloudflare-firewall.sh` on the host to manage traffic at the `DOCKER-USER` chain level:

- **Enable Mode:**
  - Automatically download the latest Cloudflare IP ranges (both IPv4 and IPv6) from the Cloudflare API.
  - Clear previous Cloudflare rules in the `DOCKER-USER` chain.
  - Allow traffic to the Docker Nginx port only if it originates from Cloudflare IP addresses or local loopback/private subnets.
  - Block all other direct ingress connections targeting the Docker containers on exposed host ports.
- **Disable Mode:** Clear all injected rules in the `DOCKER-USER` chain to allow unrestricted direct access for local testing.

## 4. Architectural Compatibility

- **Host Firewall Compatibility:** Rules are strictly appended to the `DOCKER-USER` chain, leaving the standard host `INPUT` chain intact (ensuring SSH, node exporters, and local host services remain unaffected).
- **fail2ban Integration:** Nginx logs inside the container will be mounted to the host filesystem. Since Nginx restores the real client IP from Cloudflare, fail2ban on the host can scan logs and trigger blocking actions (such as Cloudflare API blocklist updates or Nginx reload lists).

## 5. Scope of Code Changes

- `docker-compose.prod.yml`: Remove exposed ports for `api` and `session-manager`. Adjust `frontend` port exposure.
- `frontend/nginx.conf`: Add `/novnc/` proxy rules with WebSocket upgrade support, and Cloudflare trusted proxy IP configurations.
- `backend/admin_routes.py`: Update the noVNC URL generation logic.
- `scripts/setup-cloudflare-firewall.sh`: [NEW] Setup script with enable/disable commands.
