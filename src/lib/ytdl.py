from dataclasses import dataclass
import os
import sys
import glob
import shutil
import time
import subprocess
import re
from typing import Tuple

from .utils import log
from .envutils import YTSPLEET_DEFAULT_OUTPUT_FOLDER


def ytdl_log(*msgs: str):
    log("S1 (YTDL)", *msgs)


def run_ytdl(video_path: str) -> Tuple[str, str]:

    ytdl_base_format_string = '%(title)s-%(id)s'

    ytdl_full_format_string = f'{YTSPLEET_DEFAULT_OUTPUT_FOLDER}/{ytdl_base_format_string}/{ytdl_base_format_string}.%(ext)s'

    # We have to do this in order to get the correct filename,
    # Since there's no easy way to do it when fetching the mp3.
    # It will use the fetched version, so it won't run twice.
    ytdl_log("...getting video name")
    process = subprocess.Popen(
        [
            '/init',
            '-x',
            '-o',
            ytdl_full_format_string,
            '--get-filename',
            video_path
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    filename_stdout, filename_stderr = process.communicate()
    print(f'filename_stdout {filename_stdout}')

    # We must make our output directory if it doesn't already exist, or youtube-dl will fail.
    output_abspath = os.path.abspath(filename_stdout)
    # os.makedirs(os.path.dirname(output_abspath), exist_ok=True)

    path_without_ext = os.path.splitext(filename_stdout)[0].decode('utf8')

    mp3_path = os.path.abspath(f'{path_without_ext}.mp3')

    # Step 1: Use youtube-dl to download the mp3 file.
    ytdl_log("...fetching video and converting to mp3")
    process = subprocess.Popen(
        [
            '/init',
            '-x',
            '-o',
            ytdl_full_format_string,
            '--audio-format',
            'mp3',
            video_path
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    download_stdout, download_stderr = process.communicate()

    # print('YTDL: stdout')
    # for l in str(download_stdout).split('\\n'):
    #     print(f'\t{l}')

    # print('YTDL: stderr')
    # for l in str(download_stderr).split('\\n'):
    #     print(f'\t{l}')

    if (not os.path.exists(mp3_path)):
        raise Exception(
            f"Error encountered running youtube-dl. mp3_path not found after youtube-dl: {mp3_path}. Stderr follows: {download_stderr}")

    return mp3_path
