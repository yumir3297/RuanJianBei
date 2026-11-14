# Candidate Linux runtime definition. Resolve and pin a platform digest/complete
# wheel lock only after the target CPU/OS is confirmed; see docs/deployment/RUNTIME.md.
ARG PYTHON_BASE_IMAGE=python:3.13.16-slim-bookworm
FROM ${PYTHON_BASE_IMAGE}
ARG SOURCE_SHA=unknown
LABEL org.opencontainers.image.revision=${SOURCE_SHA}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 guide \
    && useradd --uid 10001 --gid guide --home-dir /home/guide --create-home --shell /usr/sbin/nologin guide \
    && mkdir -p /app/backend /app/data/processed /var/lib/scenic-guide /var/cache/huggingface \
    && chown -R 10001:10001 /app /var/lib/scenic-guide /var/cache/huggingface

WORKDIR /app/backend
COPY backend/requirements.txt /app/backend/requirements.txt
# This install is for candidate image construction. Production reproducibility
# requires the platform-specific, hash-locked file generated after target confirmation.
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY backend/ /app/backend/
COPY data/processed/ /app/data/processed/
RUN chown -R 10001:10001 /app

USER 10001:10001
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
