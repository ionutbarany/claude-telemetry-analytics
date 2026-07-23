# Production-style image for the FastAPI telemetry API.
# Build from repo root: docker build -f docker/api.Dockerfile .

FROM python:3.12-slim

# Match the project Python version and keep the runtime image small.
# Slim excludes build toolchains we do not need because deps ship as wheels.

# Avoid writing .pyc files into the image and stream logs without buffering.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies before copying app code so Docker reuses this layer
# when only application files change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the API package; add shared packages here as the monorepo grows.
COPY app/ ./app/

# Run as a dedicated non-root user to limit privilege if the container is compromised.
RUN groupadd --system appuser \
    && useradd --system --gid appuser --home-dir /home/appuser --create-home appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

# Uvicorn serves the FastAPI ASGI app; bind on all interfaces for container networking.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
