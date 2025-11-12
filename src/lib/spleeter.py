from dataclasses import dataclass
import os
import sys
import glob
import shutil
import time
import subprocess
import re
from typing import Tuple, Optional

from .envutils import YTSPLEET_DEFAULT_OUTPUT_FOLDER


def run_spleeter(mp3_path: str, output_folder: Optional[str] = None) -> Tuple[str, str]:
    # Use custom output folder if provided, otherwise use default
    base_output_folder = output_folder if output_folder else YTSPLEET_DEFAULT_OUTPUT_FOLDER
    
    process = subprocess.Popen(['spleeter', 'separate', '-o', f'{base_output_folder}', '-f', '{filename}/{instrument}_{filename}.{codec}', '-c', 'mp3', f'{mp3_path}'],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE,
                               shell=False)
    stdout, stderr = process.communicate()

    print('SPLEETER: STDOUT')
    for l in str(stdout).split('\\n'):
        print(f'\t{l}')

    print('SPLEETER STDERR')
    for l in str(stderr).split('\\n'):
        print(f'\t{l}')
