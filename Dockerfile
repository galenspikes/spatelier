# Spatelier - video/audio tool (download, transcribe, etc.)
# Base: Python 3.12 slim; add ffmpeg, spatelier[web], Chromium for cookie refresh.
# Use with volume mounts for config and downloads (see README).

FROM python:3.12-slim

# Install ffmpeg (required for video/audio processing)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for safer runtime; create app dir
RUN useradd --create-home --shell /bin/bash app
WORKDIR /app

# Install spatelier with [web] (playwright, etc.) so YouTube cookie refresh works
COPY pyproject.toml setup.py README.md LICENSE ./
COPY spatelier/ ./spatelier/
RUN pip install --no-cache-dir ".[web]"

# Install Chromium for playwright (cookie refresh); put in app home so app user can use it
ENV PLAYWRIGHT_BROWSERS_PATH=/home/app/.cache/ms-playwright
RUN playwright install chromium && playwright install-deps chromium || true

# Ensure app user owns app dir and home (config, DB, temp, playwright browsers)
RUN chown -R app:app /app /home/app

USER app
ENV PATH="/home/app/.local/bin:${PATH}"

# Config and data live on mounted volumes; use XDG-style paths by default
ENV SPATELIER_CONFIG_DIR=/home/app/.config/spatelier

ENTRYPOINT ["spatelier"]
CMD ["--help"]
