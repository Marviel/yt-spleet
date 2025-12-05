from typing import Tuple, Optional
import re
import subprocess
import time
import shutil
import glob
import sys
import os
from dataclasses import dataclass
from lib.ytdl import run_ytdl, get_playlist_video_urls
from lib.demucs_processor import run_demucs
import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
import os
import sys
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.dirname(SCRIPT_DIR))


# DEBUG
# stream = os.popen('ls -l')
# ls_output = stream.read()
# print('LS: ', ls_output)
# full_path = os.path.abspath(f'./{str(mp3_path)}')
# print(f"PATH EXISTS: {mp3_path}", os.path.exists(full_path))
# ytdl_mp3_name_preformat=re.search(
#     r'\[ExtractAudio\]\s*Destination:\s*(.*\[.*\].mp3)', str(stdout)).group(1)
# ytdl_mp3_name = re.sub('[^0-9a-zA-Z]+', '-', mp3_path)
# [print('\]\s*(.*).mp3', x) for x in str(stdout).split("\n")]
# print("MATCHES", ytdl_mp3_name)
# time.sleep(1)
# Step 2: Use


def path_replace_in_basename(pattern: str, repl: str, full_path: str) -> str:
    _dirname = os.path.dirname(full_path)
    _basename = os.path.basename(full_path)
    # Substitute in the basename, as promised.
    dest_base = re.sub(pattern, repl, _basename)
    # Rejoin to create the full path.
    dest = os.path.join(_dirname, dest_base)

    return dest


def parse_timestamp(timestamp: str) -> int:
    """
    Parse a timestamp string into seconds.
    
    Accepts formats:
    - Seconds: "123" or "123s"
    - MM:SS: "2:30"
    - HH:MM:SS: "1:02:30"
    - YouTube format: "1h30m45s", "30m", "45s"
    
    Returns:
        Total seconds as integer
    """
    if not timestamp:
        return 0
    
    # Remove trailing 's' if it's just seconds (e.g., "4399s")
    if timestamp.endswith('s') and timestamp[:-1].isdigit():
        return int(timestamp[:-1])
    
    # If it's just a number, treat as seconds
    if timestamp.isdigit():
        return int(timestamp)
    
    # Parse YouTube format like "1h30m45s", "30m45s", "45s"
    yt_match = re.match(r'^(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$', timestamp)
    if yt_match and any(yt_match.groups()):
        hours = int(yt_match.group(1) or 0)
        minutes = int(yt_match.group(2) or 0)
        seconds = int(yt_match.group(3) or 0)
        return hours * 3600 + minutes * 60 + seconds
    
    # Parse HH:MM:SS or MM:SS format
    parts = timestamp.split(':')
    if len(parts) == 2:
        return int(parts[0]) * 60 + int(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    else:
        raise ValueError(f"Invalid timestamp format: {timestamp}")


def extract_timestamp_from_url(url: str) -> Optional[str]:
    """
    Extract timestamp from YouTube URL if present.
    
    Looks for ?t= or &t= parameters in various formats:
    - t=123 (seconds)
    - t=123s (seconds with suffix)
    - t=1h30m45s (YouTube format)
    
    Returns:
        Timestamp string or None if not found
    """
    # Match t= parameter with various formats
    match = re.search(r'[?&]t=(\d+[hms]*(?:\d+[ms]*)*(?:\d+s?)?|\d+)', url)
    if match:
        return match.group(1)
    return None


def format_timestamp(seconds: int) -> str:
    """Convert seconds to HH:MM:SS format."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


@dataclass
class YTSpleetSingleFileArgs:
    source_youtube_url: str
    output_folder: Optional[str] = None
    po_token: Optional[str] = None
    dl_only: bool = False
    split_chapters: bool = False
    timestamp: Optional[str] = None
    window: Optional[int] = None  # minutes on each side (None = no extraction)


def ytspleet_single_file(args: YTSpleetSingleFileArgs):
    print("--------------------------")
    print("STARTING STEP 1: youtube-dl (YTDL)")
    print("--------------------------")
    
    # Calculate time range if timestamp/window extraction is requested
    time_range = None
    timestamp = args.timestamp
    window = args.window
    
    # If window is set but no timestamp, try to extract timestamp from URL
    if window is not None and not timestamp:
        url_timestamp = extract_timestamp_from_url(args.source_youtube_url)
        if url_timestamp:
            timestamp = url_timestamp
            print(f"Found timestamp in URL: {timestamp}")
        else:
            print(f"Warning: --window specified but no timestamp found in URL. Use --timestamp to specify.")
    
    # If we have a timestamp and window, calculate the time range
    if timestamp and window is not None:
        center_seconds = parse_timestamp(timestamp)
        window_seconds = window * 60
        start_seconds = max(0, center_seconds - window_seconds)
        end_seconds = center_seconds + window_seconds
        time_range = (format_timestamp(start_seconds), format_timestamp(end_seconds))
        print(f"Extracting time range: {time_range[0]} to {time_range[1]} (centered on {timestamp}, ±{window}min)")
    elif timestamp and window is None:
        # Timestamp provided but no window - default to 4 minutes each side
        window = 4
        center_seconds = parse_timestamp(timestamp)
        window_seconds = window * 60
        start_seconds = max(0, center_seconds - window_seconds)
        end_seconds = center_seconds + window_seconds
        time_range = (format_timestamp(start_seconds), format_timestamp(end_seconds))
        print(f"Extracting time range: {time_range[0]} to {time_range[1]} (centered on {timestamp}, ±{window}min)")
    
    mp3_path = run_ytdl(args.source_youtube_url, args.po_token, args.output_folder, args.split_chapters, time_range)

    if args.dl_only or args.split_chapters:
        print("--------------------------")
        if args.split_chapters:
            print("Download complete (--split-chapters mode, skipping stem separation)")
        else:
            print("Download complete (--dl-only mode, skipping stem separation)")
        print("--------------------------")
        print(f"Output: '{mp3_path}'")
        return

    print("--------------------------")
    print("STARTING STEP 2: Demucs")
    print("--------------------------")
    output_dir, _ = run_demucs(mp3_path, args.output_folder)

    print(f"Processing complete. Output files in: '{output_dir}'")
    print("Files:", os.listdir(output_dir))


def expand_playlist_urls(urls: list[str], full_playlist: bool) -> list[str]:
    """
    Expand URLs to include all videos from playlists if --full-playlist is set.
    
    Args:
        urls: List of YouTube URLs
        full_playlist: Whether to expand playlist URLs
        
    Returns:
        Expanded list of video URLs
    """
    if not full_playlist:
        return urls
    
    expanded_urls = []
    for url in urls:
        # Check if URL contains a playlist parameter
        if 'list=' in url:
            print(f"Expanding playlist: {url}")
            try:
                playlist_urls = get_playlist_video_urls(url)
                expanded_urls.extend(playlist_urls)
                print(f"  Added {len(playlist_urls)} videos from playlist")
            except Exception as e:
                print(f"  Warning: Failed to expand playlist, using original URL: {e}")
                expanded_urls.append(url)
        else:
            expanded_urls.append(url)
    
    return expanded_urls


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--urls', nargs='+', required=True, help='YouTube URLs to download and process')
    parser.add_argument('--po-token', help='YouTube PO token for authentication (optional, helps with DRM issues)')
    parser.add_argument('--cookies', help='Path to cookies file for YouTube authentication (optional)')
    parser.add_argument('-o', '--output-folder', help='Custom output folder path (optional, overrides default)')
    parser.add_argument('--dl-only', action='store_true', help='Only download audio, skip stem separation')
    parser.add_argument('--full-playlist', action='store_true', help='Download all videos from playlist URLs')
    parser.add_argument('--split-chapters', action='store_true', help='Split video into separate files by chapter (implies --dl-only)')
    parser.add_argument('--timestamp', '-t', help='Center timestamp for extraction (formats: "123", "2:30", "1:02:30", or auto-detected from URL)')
    parser.add_argument('--window', '-w', type=int, default=None, help='Minutes on each side of timestamp (default: 4 when -t used). Enables URL timestamp detection.')
    parsed = parser.parse_args()

    # Expand playlist URLs if requested
    urls = expand_playlist_urls(parsed.urls, parsed.full_playlist)
    print(f"Processing {len(urls)} video(s)")

    # Set the number of processes to the number of URLs or your preferred limit
    max_workers = len(urls)  # Or set a fixed number like 4 or 8, etc.

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(ytspleet_single_file, YTSpleetSingleFileArgs(
            url, parsed.output_folder, parsed.po_token, parsed.dl_only, 
            parsed.split_chapters, parsed.timestamp, parsed.window
        )) for url in urls]
        for future in futures:
            # If you need to handle results or exceptions, do it here
            try:
                result = future.result()  # This will block until the future is completed
                print("Process completed successfully", result)
            except Exception as exc:
                print("Generated an exception: ", exc)

if __name__ == "__main__":
    main()
