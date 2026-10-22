# NextRun API (CPU). For GPU inference use an nvidia/cuda base image and drop the CPU torch index.
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 ffmpeg \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/nextrun_cv src/nextrun_cv
# editable: nextrun_cv finds models/ and data/venues/ relative to /app
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -e ".[detect,api]"
COPY models models
COPY data/venues data/venues

ENV NEXTRUN_DATA=/app/results/games
EXPOSE 8000
CMD ["uvicorn", "nextrun_cv.api:app", "--host", "0.0.0.0", "--port", "8000"]
