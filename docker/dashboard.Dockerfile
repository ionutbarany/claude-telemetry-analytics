# Production-style image for the Streamlit telemetry dashboard.
# Build from repo root: docker build -f docker/dashboard.Dockerfile .

FROM python:3.12-slim

# Match the project Python version and keep the runtime image small.
# Slim excludes build toolchains we do not need because deps ship as wheels.

# Avoid writing .pyc files into the image and stream logs without buffering.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies before copying dashboard code so Docker reuses this layer
# when only application files change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the dashboard package; add shared packages here as the monorepo grows.
COPY dashboard/ ./dashboard/

# Run as a dedicated non-root user to limit privilege if the container is compromised.
RUN groupadd --system appuser \
    && useradd --system --gid appuser --home /app appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8501

# Bind Streamlit on all interfaces so the service is reachable from outside the container.
CMD [
    "streamlit", "run", "dashboard/Home.py",
    "--server.address", "0.0.0.0",
    "--server.port", "8501",
]
