# YT-Spleet

## Installation

1. Install Docker Desktop for your system
2. (WINDOWS ONLY) Enable WSL2
3. Open a terminal or command prompt window & pull this image from Dockerhub:
   `docker pull lukebechtel/yt-spleet:latest`

## Running

1. Figure out what directory you want the files to be saved to on your computer
   -- `YOUR_DIR`
2. Run this command, replacing `YOUR_DIR` with that directory path, and
   `YOUR_YOUTUBE_URL` with the URL you want to download and split.
   `docker run -v YOUR_DIR:/src/yt-spleet-output/ -it lukebechtel/yt-spleet:latest --urls "YOUR_YOUTUBE_URL"`
3. Wait for the download and split to finish. Normal sized (< 5 minute) files
   should take less than one minute.
4. Check the `YOUR_DIR` directory for the files. There will be a new folder for
   each URL you passed in, and each folder will contain the split audio files,
   along with the original.

## Building locally (ADVANCED)

### Building

`docker build . -f Dockerfile -t yt-spleet:latest`
