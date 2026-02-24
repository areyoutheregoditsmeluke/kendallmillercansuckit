# ── Build stage ──────────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt && \
    pip install --no-cache-dir --prefix=/install supervisor

# ── Runtime stage ────────────────────────────────────────────────────────────
FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends git tini && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local

RUN mkdir -p /data /repo /app

COPY server.py telegram_bot.py git_poller.py /app/
COPY supervisord.conf /etc/supervisord.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

WORKDIR /app

EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import requests; r=requests.get('http://localhost:8765/health'); r.raise_for_status()"

ENTRYPOINT ["tini", "--"]
CMD ["/entrypoint.sh"]
