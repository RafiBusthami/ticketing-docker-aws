# ticket-api image: Flask + gunicorn on Python 3.12 (slim).
# Base image comes from Amazon ECR Public (no Docker Hub pull limits on AWS).
FROM public.ecr.aws/docker/library/python:3.12-slim

ARG APP_VERSION=dev
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_VERSION=${APP_VERSION} \
    DB_PATH=/data/tickets.db

WORKDIR /app

# Apply the latest Debian security updates (ECR scan found HIGH CVEs in
# openssl, glibc and zlib of the base image; fixed versions are available)
RUN apt-get update \
 && apt-get upgrade -y --no-install-recommends \
 && rm -rf /var/lib/apt/lists/*

# Install dependencies first so this layer is cached between code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Run as a non-root user; /data holds the SQLite database (mounted volume)
RUN useradd --uid 10001 --no-create-home appuser \
 && mkdir -p /data && chown appuser /data
USER appuser
VOLUME ["/data"]

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health').status==200 else 1)"

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "2", "--access-logfile", "-", "app:app"]
