from typing import Tuple, Optional
import re
import subprocess
import time
import shutil
import glob
import sys
import os
from dataclasses import dataclass
from lib.ytdl import run_ytdl
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
    po_token: Optional[str] = None


def ytspleet_single_file(args: YTSpleetSingleFileArgs):
    print("--------------------------")
    print("STARTING STEP 1: youtube-dl (YTDL)")
    print("--------------------------")
    mp3_path = run_ytdl(args.source_youtube_url, args.po_token)

    print("--------------------------")
    print("STARTING STEP 2: Demucs")
    print("--------------------------")
    output_dir, _ = run_demucs(mp3_path)

    print(f"Processing complete. Output files in: '{output_dir}'")
    print("Files:", os.listdir(output_dir))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--urls', nargs='+', required=True, help='YouTube URLs to download and process')
    parser.add_argument('--po-token', help='YouTube PO token for authentication (optional, helps with DRM issues)')
    parser.add_argument('--cookies', help='Path to cookies file for YouTube authentication (optional)')
    parsed = parser.parse_args()

    # Set the number of processes to the number of URLs or your preferred limit
    max_workers = len(parsed.urls)  # Or set a fixed number like 4 or 8, etc.

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(ytspleet_single_file, YTSpleetSingleFileArgs(url, parsed.po_token)) for url in parsed.urls]
        for future in futures:
            # If you need to handle results or exceptions, do it here
            try:
                result = future.result()  # This will block until the future is completed
                print("Process completed successfully", result)
            except Exception as exc:
                print("Generated an exception: ", exc)

if __name__ == "__main__":
    main()
