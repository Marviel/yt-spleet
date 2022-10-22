from dataclasses import dataclass
import os
import sys
import glob
import shutil
import time
import subprocess
import re
from typing import Tuple


def log(prefix: str, *msgs: str):
    print(f'[{prefix}]:', *msgs)
