from dataclasses import dataclass
import os
import sys
import glob
import shutil
import time
import subprocess
import re
import threading
from typing import Tuple, List, Callable


def log(prefix: str, *msgs: str):
    print(f'[{prefix}]:', *msgs)


def run_subprocess_with_realtime_output(cmd: List[str], log_func: Callable, log_prefix: str = "") -> Tuple[int, str, str]:
    """
    Run a subprocess and print its output in real time.
    
    Args:
        cmd: Command to run as a list of strings
        log_func: Function to use for logging
        log_prefix: Prefix for log messages
        
    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1
    )
    
    stdout_lines = []
    stderr_lines = []
    
    # Function to handle output stream
    def handle_stream(stream, lines_list, stream_name):
        for line in iter(stream.readline, ''):
            if not line:
                break
            line = line.rstrip()
            lines_list.append(line)
            log_func(f"{log_prefix} {stream_name}: {line}")
            sys.stdout.flush()  # Ensure output is displayed immediately
    
    # Use threads to read stdout and stderr concurrently
    stdout_thread = threading.Thread(
        target=handle_stream, 
        args=(process.stdout, stdout_lines, "STDOUT")
    )
    stderr_thread = threading.Thread(
        target=handle_stream, 
        args=(process.stderr, stderr_lines, "STDERR")
    )
    
    stdout_thread.daemon = True
    stderr_thread.daemon = True
    stdout_thread.start()
    stderr_thread.start()
    
    # Wait for the process to complete
    return_code = process.wait()
    
    # Wait for the threads to finish
    stdout_thread.join()
    stderr_thread.join()
    
    return return_code, '\n'.join(stdout_lines), '\n'.join(stderr_lines)
