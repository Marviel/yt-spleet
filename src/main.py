
from typing import Tuple
import re
import subprocess
import time
import shutil
import glob
import sys
import os
from dataclasses import dataclass
from lib.ytdl import run_ytdl
from lib.spleeter import run_spleeter
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


def ytspleet_single_file(args: YTSpleetSingleFileArgs):
    print("--------------------------")
    print("STARTING STEP 1: youtube-dl (YTDL)")
    print("--------------------------")
    mp3_path = run_ytdl(args.source_youtube_url)

    print("--------------------------")
    print("STARTING STEP 2: Spleeter")
    print("--------------------------")
    run_spleeter(mp3_path)

    dirpath = os.path.dirname(mp3_path)

    for src in glob.glob(f'{dirpath}/accompaniment_*'):

        dest = path_replace_in_basename('^accompaniment_(.*)', r'acc_\1', src)

        shutil.move(src, dest)

    for src in glob.glob(f'{dirpath}/vocals*'):
        print(f"vocals {src}")

        dest = path_replace_in_basename('^vocals_(.*)', r'voc_\1', src)

        shutil.move(src, dest)


def main():
    import argparse

    parser = argparse.ArgumentParser()

    # This is the correct way to handle accepting multiple arguments.
    # '+' == 1 or more.
    # '*' == 0 or more.
    # '?' == 0 or 1.
    # An int is an explicit number of arguments to accept.
    parser.add_argument('--urls', nargs='+')

    parsed = parser.parse_args()

    # To show the results of the given option to screen.
    for i, url in enumerate(parsed.urls):
        if url is not None:
            print(f"YT-SPLEET: Running url ({i}/{len(parsed.urls)}): {url}")
            ytspleet_single_file(
                YTSpleetSingleFileArgs(source_youtube_url=url))


if __name__ == "__main__":
    main()
