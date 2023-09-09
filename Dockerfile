
# Base image supports Nvidia CUDA but does not require it and can also run demucs on the CPU
FROM nvidia/cuda:11.8.0-base-ubuntu22.04

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
    python3 \
    python3-dev \
    python3-pip \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Clone Facebook Demucs
RUN git clone -b main --single-branch https://github.com/facebookresearch/demucs /lib/demucs
WORKDIR /lib/demucs

# Install dependencies
RUN python3 -m pip install -e . --no-cache-dir
# Run once to ensure demucs works and trigger the default model download
RUN python3 -m demucs -d cpu test.mp3 
# Cleanup output - we just used this to download the model
RUN rm -r separated


# # Install dependencies
# RUN apt-get update
# RUN apt-get install -y gfortran liblapack-dev


# # Install youtube-dl
# RUN pip install numpy
RUN pip install --upgrade yt-dlp
# RUN curl -L https://yt-dl.org/downloads/latest/youtube-dl -o /usr/local/bin/youtube-dl
# RUN pip install --upgrade yt-dlp
# RUN chmod a+rx /usr/local/bin/youtube-dl
# RUN pip install --upgrade --force-reinstall "git+https://github.com/ytdl-org/youtube-dl.git"

# Make yt-dlp youtube-dl with alias
RUN ln -s /usr/local/bin/yt-dlp /usr/local/bin/youtube-dl

# # Install spleeter
RUN pip install spleeter

COPY src/ /src

# #RUN pip3 uninstall --break-system-packages -y tensorflow tensorflow-cpu
# #RUN pip3 install --break-system-packages tensorflow-aarch64 -f https://tf.kmtea.eu/whl/stable.html

WORKDIR /src/

# Run a conversion so that we precache the results.
RUN python3 /src/main.py --urls "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

ENTRYPOINT ["python3", "/src/main.py"]


# VOLUME /data/input
# VOLUME /data/output
# VOLUME /data/models

# ENTRYPOINT ["/bin/bash", "--login", "-c"]

