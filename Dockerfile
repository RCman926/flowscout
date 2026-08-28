FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLOWSCOUT_CLOUD=1 \
    PAPER_AUTO_ARMED=false \
    IBKR_ENABLED=0 \
    UNATTENDED=0 \
    FLOWSCOUT_HOST=0.0.0.0

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /data

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Railway injects PORT. Local docker-compose uses 8000.
HEALTHCHECK --interval=30s --timeout=8s --start-period=90s --retries=5 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/healthz'%os.environ.get('PORT','8000'), timeout=5)"

CMD ["python", "zerodte_websocket_server.py"]
