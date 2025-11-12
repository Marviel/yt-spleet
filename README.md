# YT-Spleet with Demucs

A tool to download YouTube videos and split the audio into vocals and accompaniment using Demucs.

1. Install Docker Desktop for your system
2. (WINDOWS ONLY) Enable WSL2
3. Open a terminal or command prompt window & pull this image from Dockerhub:
   `docker pull lukebechtel/yt-spleet:latest`

- Download audio from YouTube videos using yt-dlp
- Process audio with Demucs to separate vocals from accompaniment
- Process multiple URLs in parallel
- Output files are renamed for consistency
- Direct access to YouTube metadata via the YouTube API

1. Figure out what directory you want the files to be saved to on your computer
   -- `YOUR_DIR`
2. Run this command, replacing `YOUR_DIR` with that directory path, and
   `YOUR_YOUTUBE_URL` with the URL you want to download and split.
   `docker run -v YOUR_DIR:/src/yt-spleet-output/ --rm -it lukebechtel/yt-spleet:latest --urls "YOUR_YOUTUBE_URL"`
3. Wait for the download and split to finish. Normal sized (< 5 minute) files
   should take less than one minute.
4. Check the `YOUR_DIR` directory for the files. There will be a new folder for
   each URL you passed in, and each folder will contain the split audio files,
   along with the original.

- Docker (recommended for easy setup)
- Python 3.10+ (if running without Docker)
- ffmpeg

## Usage

### With Docker (recommended)

1. Build the Docker image:
```bash
docker build -t yt-spleet .
```

2. Run the container with your YouTube URLs:
```bash
docker run -v $(pwd)/yt-spleet-output:/src/yt-spleet-output yt-spleet --urls "https://www.youtube.com/watch?v=VIDEO_ID_1" "https://www.youtube.com/watch?v=VIDEO_ID_2"
```

### Without Docker

1. Install `uv`

2. Install the required dependencies:
```bash
uv pip install yt-dlp demucs
```

2. Run the script:
```bash
uv run python src/main.py --urls "https://www.youtube.com/watch?v=VIDEO_ID_1" "https://www.youtube.com/watch?v=VIDEO_ID_2"
```

## Handling YouTube DRM Issues

YouTube has been experimenting with applying DRM to videos when accessed through certain clients. If you encounter download issues, you can try the following solutions:

### Using a PO Token

A PO token can help bypass DRM restrictions. To use a PO token:

1. Follow the [PO Token Guide](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide) to obtain a token
2. Run the script with the token:
```bash
python src/main.py --urls "https://www.youtube.com/watch?v=VIDEO_ID" --po-token "YOUR_PO_TOKEN"
```

Or with Docker:
```bash
docker run -v $(pwd)/yt-spleet-output:/src/yt-spleet-output yt-spleet --urls "https://www.youtube.com/watch?v=VIDEO_ID" --po-token "YOUR_PO_TOKEN"
```

### Using Cookies

You can also use cookies from your browser:

1. Export cookies from your browser (using a browser extension or yt-dlp's `--cookies-from-browser` option)
2. Save them to `~/.config/yt-dlp/cookies.txt`

The script will automatically try to use these cookies if the initial download fails.

## Output

The output files will be in the `yt-spleet-output/TITLE-ID` directory with the following naming convention:
- Original MP3: `TITLE-ID.mp3`
- Vocals track: `yts-vox_TITLE-ID.mp3` (renamed from `vocals_TITLE-ID.mp3`)
- Accompaniment track: `yts-acc_TITLE-ID.mp3` (renamed from `no_vocals_TITLE-ID.mp3`)

## How It Works

1. **Metadata Retrieval**: The tool first retrieves the video title directly from the YouTube API.

2. **Download**: Using the retrieved metadata, the tool creates a consistent file structure and uses yt-dlp to download the audio from YouTube videos in MP3 format.

3. **Separation**: Demucs processes the MP3 file to separate vocals from accompaniment.
   - Demucs creates output files in its own directory structure (`yt-spleet-output/htdemucs/TRACK_NAME/`)
   - The tool then copies these files to the original directory where the MP3 is located

4. **Renaming**: Files are renamed to a consistent format:
   - `vocals_TITLE-ID.mp3` → `yts-vox_TITLE-ID.mp3`
   - `no_vocals_TITLE-ID.mp3` → `yts-acc_TITLE-ID.mp3`

After processing, all files (original MP3, vocals, and accompaniment) will be in the same directory.

## About Demucs

Demucs is a state-of-the-art music source separation model developed by Facebook Research. It can separate music into different stems (vocals, drums, bass, and other). In this project, we use it in two-stem mode to separate vocals from accompaniment.

## License

This project is open source and available under the MIT License.

# FEATURES
- [ ] Download youtube yrul
- [ ] Be able to spe