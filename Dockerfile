# Base image supports Nvidia CUDA but does not require it and can also run demucs on the CPU
FROM python:3.10-slim

USER root
ENV TORCH_HOME=/data/models

# Install required tools
# Notes:
#  - build-essential and python3-dev are included for platforms that may need to build some Python packages (e.g., arm64)
#  - torchaudio >= 0.12 now requires ffmpeg on Linux, see https://github.com/facebookresearch/demucs/blob/main/docs/linux.md
RUN apt update && apt install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install yt-dlp (modern replacement for youtube-dl)
# Using the latest version to handle YouTube DRM issues
RUN pip install --upgrade yt-dlp
RUN pip install --upgrade spleeter

# Make yt-dlp youtube-dl with alias
RUN ln -s /usr/local/bin/yt-dlp /usr/local/bin/youtube-dl

# Install Demucs for audio separation
RUN python3 -m pip install -U demucs

# Create directory for cookies
RUN mkdir -p /root/.config/yt-dlp

COPY src/ /src

WORKDIR /src/

# Run a conversion so that we precache the results.
# Note: This may fail if YouTube applies DRM to the test video
# In that case, you may need to provide a PO token when running the container
RUN python3 /src/main.py --urls "https://www.youtube.com/watch?v=dQw4w9WgXcQ" || echo "Precache failed, but continuing build"

ENTRYPOINT ["python3", "/src/main.py"]

# VOLUME /data/input
# VOLUME /data/output
# VOLUME /data/models

# ENTRYPOINT ["/bin/bash", "--login", "-c"]

