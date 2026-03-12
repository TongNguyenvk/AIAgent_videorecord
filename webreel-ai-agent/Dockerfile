# ============================================================
# AI Video Tutor — Final Optimized Multi-stage Dockerfile
# ============================================================

# ------ Stage 1: Build Webreel (Node.js) ------
FROM node:20-slim AS webreel-builder

WORKDIR /build

RUN corepack enable && corepack prepare pnpm@latest --activate

# Layer Caching cho dependencies
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY packages/@webreel/core/package.json ./packages/@webreel/core/
COPY packages/webreel/package.json ./packages/webreel/

RUN pnpm install --frozen-lockfile --prefer-offline

# Build mã nguồn
COPY packages/@webreel/core/src ./packages/@webreel/core/src
COPY packages/@webreel/core/tsconfig.json ./packages/@webreel/core/
COPY packages/webreel/src ./packages/webreel/src
COPY packages/webreel/tsconfig.json ./packages/webreel/
COPY tsconfig.json ./

RUN pnpm --filter @webreel/core build && pnpm --filter webreel build


# ------ Stage 2: Python + Node Runtime (Production) ------
FROM python:3.12-slim

WORKDIR /app

# Quy hoạch biến môi trường chuẩn chỉ
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PYTHONPATH=/app/webreel-ai-agent \
    NODE_ENV=production \
    CHROME_HEADLESS_PATH=/root/.webreel/bin/chrome-headless-shell/chrome-headless-shell-linux64/chrome-headless-shell \
    FFMPEG_PATH=/usr/bin/ffmpeg

# 1. Cài đặt System Deps & Node.js (Ép IPv4 chống treo mạng)
# Debian Bookworm (base của python:3.12-slim) sẽ tự cài Node.js v18/v20 ổn định
RUN apt-get -o Acquire::ForceIPv4=true update && \
    apt-get -o Acquire::ForceIPv4=true install -y --no-install-recommends \
    curl gnupg ca-certificates ffmpeg git unzip nodejs npm \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/*

RUN npm install -g pnpm

# 2. Cài đặt Python Dependencies
COPY webreel-ai-agent/requirements.txt /tmp/requirements.txt

# Nâng cấp công cụ build trước (setuptools, wheel) để giải quyết bài toán build moviepy từ source
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Cài đặt requirements bằng repo PyPI mặc định (Bỏ Tsinghua để tránh lỗi IPv6)
RUN pip install --no-cache-dir --default-timeout=100 -r /tmp/requirements.txt \
    && rm /tmp/requirements.txt

# 3. Cài trình duyệt cho Python Playwright
RUN playwright install-deps chromium \
    && playwright install chromium

# 4. Copy và setup Webreel từ Stage 1
COPY --from=webreel-builder /build/package.json /build/pnpm-workspace.yaml /build/pnpm-lock.yaml ./
COPY --from=webreel-builder /build/packages/@webreel/core/package.json ./packages/@webreel/core/
COPY --from=webreel-builder /build/packages/webreel/package.json ./packages/webreel/

RUN pnpm install --prod --frozen-lockfile --ignore-scripts

COPY --from=webreel-builder /build/packages/webreel/dist ./packages/webreel/dist
COPY --from=webreel-builder /build/packages/@webreel/core/dist ./packages/@webreel/core/dist

# Tải Headless-shell cho Webreel
RUN node packages/webreel/dist/index.js install

# 5. Nạp mã nguồn Agent
COPY webreel-ai-agent/browser-use ./webreel-ai-agent/browser-use
COPY webreel-ai-agent/src ./webreel-ai-agent/src
COPY webreel-ai-agent/run_pipeline.py ./webreel-ai-agent/
COPY webreel-ai-agent/.env.example ./webreel-ai-agent/.env

ENV PATH="/root/.webreel/bin:${PATH}"
RUN mkdir -p /app/output

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "webreel-ai-agent/src/app.py", "--server.port=8501", "--server.address=0.0.0.0"]