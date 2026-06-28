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

# Copy application
COPY . .

# Expose FastAPI port
EXPOSE 7860

# Default: run FastAPI server (HF Spaces expects port 7860)
# Add SSL: mount cert.pem + key.pem and set SSL_CERTFILE / SSL_KEYFILE env vars
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "4"]
