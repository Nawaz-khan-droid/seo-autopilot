FROM python:3.13-slim

WORKDIR /app

# Install system deps for Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates fonts-liberation libasound2 libatk-bridge2.0-0 \
    libatk1.0-0 libcups2 libdrm2 libgbm1 libnss3 libnspr4 \
    libu2f-udev libvulkan1 libxcomposite1 libxdamage1 libxfixes3 \
    libxkbcommon0 libxrandr2 xdg-utils wget \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium --with-deps 2>/dev/null || true

# Copy application (specific dirs only — never COPY . .)
COPY api/ api/
COPY config/ config/
COPY modules/ modules/
COPY report/ report/
COPY orchestrator/ orchestrator/
COPY scripts/ scripts/
COPY main.py run_report.py streamlit_app.py requirements.txt ./
COPY db/init.sql db/init.sql

# Expose FastAPI port
ARG PORT=8000
ENV PORT=${PORT}
EXPOSE ${PORT}

# Default: run FastAPI server
CMD uvicorn api.main:app --host 0.0.0.0 --port ${PORT} --workers ${WEB_CONCURRENCY:-4}
