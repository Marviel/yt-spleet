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
from .utils import log, run_subprocess_with_realtime_output


def demucs_log(*msgs: str):
    log("S2 (DEMUCS)", *msgs)


def run_demucs(mp3_path: str, output_folder: Optional[str] = None) -> Tuple[str, str]:
    """
    Run Demucs on the given MP3 file to separate vocals from accompaniment.
    
    Args:
        mp3_path: Path to the MP3 file to process
        output_folder: Optional custom output folder path (overrides default)
        
    Returns:
        Tuple of (output_directory, stderr)
    """
    demucs_log(f"Processing {mp3_path} with Demucs")
    
    # Get the track name (filename without extension)
    track_name = os.path.splitext(os.path.basename(mp3_path))[0]
    track_dir = os.path.dirname(mp3_path)
    
    # Use custom output folder if provided, otherwise use default
    base_output_folder = output_folder if output_folder else YTSPLEET_DEFAULT_OUTPUT_FOLDER
    
    # Create output directory if it doesn't exist
    os.makedirs(base_output_folder, exist_ok=True)
    
    # Run Demucs with the htdemucs model (best quality for vocals)
    demucs_cmd = [
        'python3', '-m', 'demucs', 
        '--out', base_output_folder,
        '--mp3', # Output as MP3 files
        '--two-stems', 'vocals', # Split into vocals and accompaniment only
        mp3_path
    ]
    
    # Run the Demucs command with real-time output
    demucs_log(f"Running Demucs on {track_name}")
    return_code, stdout, stderr = run_subprocess_with_realtime_output(
        demucs_cmd,
        demucs_log,
        "DEMUCS"
    )
    
    # Check if the process was successful
    if return_code != 0:
        raise Exception(f"Error encountered running Demucs. Return code: {return_code}. Stderr follows: {stderr}")
    
    # Demucs creates files in a structure like:
    # base_output_folder/htdemucs/TRACK_NAME/vocals.mp3
    # base_output_folder/htdemucs/TRACK_NAME/no_vocals.mp3
    
    # Find the output files
    demucs_output_dir = os.path.join(base_output_folder, 'htdemucs', track_name)
    
    if not os.path.exists(demucs_output_dir):
        demucs_log(f"Warning: Expected output directory {demucs_output_dir} not found")
        # Try to find the actual output directory
        for root, dirs, files in os.walk(base_output_folder):
            if os.path.basename(root) == track_name:
                demucs_output_dir = root
                demucs_log(f"Found alternative output directory: {demucs_output_dir}")
                break
    
    # Move all files from the Demucs output directory to the original directory with proper naming
    if os.path.exists(demucs_output_dir):
        demucs_log(f"Moving output files from {demucs_output_dir} to {track_dir}")
        
        # Define the mapping of Demucs output files to our desired naming format
        file_mapping = {
            'vocals.mp3': f'yts-vox_{track_name}.mp3',
            'no_vocals.mp3': f'yts-acc_{track_name}.mp3'
        }
        
        # Move and rename the files
        for source_name, target_name in file_mapping.items():
            source_file = os.path.join(demucs_output_dir, source_name)
            target_file = os.path.join(track_dir, target_name)
            
            if os.path.isfile(source_file):
                demucs_log(f"Moving {source_name} to {target_name}")
                shutil.move(source_file, target_file)
                demucs_log(f"Moved {source_name} to {target_name}")
            else:
                demucs_log(f"Warning: Expected file {source_file} not found")
        
        # Clean up the empty directory if possible
        try:
            if len(os.listdir(demucs_output_dir)) == 0:
                os.rmdir(demucs_output_dir)
                demucs_log(f"Removed empty directory {demucs_output_dir}")
        except Exception as e:
            demucs_log(f"Note: Could not remove directory {demucs_output_dir}: {e}")
    else:
        demucs_log(f"Warning: Could not find Demucs output directory")
    
    # Return the output directory
    return track_dir, stderr 