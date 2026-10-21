# NextRun API (CPU). For GPU inference use an nvidia/cuda base image and drop the CPU torch index.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 ffmpeg \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml README.md ./
COPY nextrun_cv nextrun_cv
COPY backend backend
# editable: nextrun_cv finds models/ and configs/ relative to /app
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -e ".[detect,api]"
COPY configs configs
COPY models models

ENV NEXTRUN_DATA=/app/outputs
EXPOSE 8000
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
