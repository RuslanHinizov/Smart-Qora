FROM python:3.12-slim-bookworm

# GPU access comes from the NVIDIA container runtime (compose `deploy.resources.devices`);
# the CUDA runtime libs ship inside the torch cu124 wheels installed below.
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 DEBIAN_FRONTEND=noninteractive \
    NVIDIA_VISIBLE_DEVICES=all NVIDIA_DRIVER_CAPABILITIES=compute,utility

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

# Split so an edit to requirements.txt does not re-download the (large) torch wheels.
COPY requirements-gpu.txt ./
RUN pip install -r requirements-gpu.txt
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
RUN useradd --create-home app && chown -R app /app
USER app

HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
    CMD curl -fsS http://localhost:8000/api/health || exit 1

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
