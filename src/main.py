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


@dataclass
class YTSpleetSingleFileArgs:
    source_youtube_url: str
    output_folder: Optional[str] = None
    po_token: Optional[str] = None
    dl_only: bool = False
    split_chapters: bool = False


def ytspleet_single_file(args: YTSpleetSingleFileArgs):
    print("--------------------------")
    print("STARTING STEP 1: youtube-dl (YTDL)")
    print("--------------------------")
    mp3_path = run_ytdl(args.source_youtube_url, args.po_token, args.output_folder, args.split_chapters)

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
    parsed = parser.parse_args()

    # Expand playlist URLs if requested
    urls = expand_playlist_urls(parsed.urls, parsed.full_playlist)
    print(f"Processing {len(urls)} video(s)")

    # Set the number of processes to the number of URLs or your preferred limit
    max_workers = len(urls)  # Or set a fixed number like 4 or 8, etc.

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(ytspleet_single_file, YTSpleetSingleFileArgs(url, parsed.output_folder, parsed.po_token, parsed.dl_only, parsed.split_chapters)) for url in urls]
        for future in futures:
            # If you need to handle results or exceptions, do it here
            try:
                result = future.result()  # This will block until the future is completed
                print("Process completed successfully", result)
            except Exception as exc:
                print("Generated an exception: ", exc)

if __name__ == "__main__":
    main()
