FROM python:3.12-slim

# Install FFmpeg
RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ src/

# Create recordings directory
RUN mkdir -p /app/recordings

# Default: run in CLI mode (no GUI in Docker)
ENTRYPOINT ["python", "-m", "src"]

# Override with username, e.g.: docker run tiktok-recorder username123
CMD ["--help"]
