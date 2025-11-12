from dataclasses import dataclass
import os
import sys
import glob
import shutil
import time
import subprocess
import re
import json
import urllib.request
import urllib.parse
from typing import Tuple, Optional

from .utils import log, run_subprocess_with_realtime_output
from .envutils import YTSPLEET_DEFAULT_OUTPUT_FOLDER


def ytdl_log(*msgs: str):
    log("S1 (YTDL)", *msgs)


def get_video_id(url: str) -> str:
    """
    Extract the video ID from a YouTube URL.
    
    Args:
        url: YouTube URL
        
    Returns:
        YouTube video ID
    """
    # Extract video ID from URL
    video_id = None
    
    # Try to match the standard YouTube URL pattern
    match = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)', url)
    if match:
        video_id = match.group(1)
    
    if not video_id:
        raise ValueError(f"Could not extract video ID from URL: {url}")
    
    return video_id


def get_video_title(video_id: str) -> str:
    """
    Get the title of a YouTube video using the oEmbed API.
    
    Args:
        video_id: YouTube video ID
        
    Returns:
        Video title
    """
    ytdl_log(f"Getting title for video ID: {video_id}")
    
    # Use YouTube's oEmbed API to get video metadata
    oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    
    try:
        with urllib.request.urlopen(oembed_url) as response:
            data = json.loads(response.read().decode())
            title = data.get('title')
            
            if not title:
                raise ValueError(f"Could not get title for video ID: {video_id}")
            
            # Clean the title to make it suitable for a filename
            title = re.sub(r'[^\w\s-]', '', title)  # Remove special characters
            title = re.sub(r'\s+', ' ', title).strip()  # Normalize whitespace
            
            ytdl_log(f"Video title: {title}")
            return title
    except Exception as e:
        ytdl_log(f"Error getting video title: {e}")
        # Fall back to using the video ID as the title
        return video_id


def run_ytdl(video_path: str, po_token: Optional[str] = None, output_folder: Optional[str] = None) -> str:
    """
    Run youtube-dl to download a video and convert it to MP3.
    
    Args:
        video_path: YouTube URL to download
        po_token: Optional PO token to use for authentication
        output_folder: Optional custom output folder path (overrides default)
        
    Returns:
        Path to the downloaded MP3 file
    """
    # Extract video ID and get title
    video_id = get_video_id(video_path)
    video_title = get_video_title(video_id)
    
    # Create a clean filename with title and ID
    clean_filename = f"{video_title}-{video_id}"
    
    # Use custom output folder if provided, otherwise use default
    base_output_folder = output_folder if output_folder else YTSPLEET_DEFAULT_OUTPUT_FOLDER
    
    # Create output directory structure
    output_dir = os.path.join(base_output_folder, clean_filename)
    os.makedirs(output_dir, exist_ok=True)
    
    # Define the output MP3 path
    mp3_path = os.path.join(output_dir, f"{clean_filename}.mp3")
    mp3_path = os.path.abspath(mp3_path)
    
    # If the file already exists, return its path
    if os.path.exists(mp3_path):
        ytdl_log(f"File already exists: {mp3_path}")
        return mp3_path
    
    # Base command with alternative clients to avoid DRM issues
    ytdl_cmd = [
        'youtube-dl',
        '-x',
        '--audio-format', 'mp3',
        '-o', os.path.join(output_dir, f"{clean_filename}.%(ext)s"),
        '--extractor-args',
        'youtube:player-client=default,-tv,web_safari,web_embedded',  # Use alternative clients, avoid TV client
    ]
    
    # Add PO token if provided
    if po_token:
        ytdl_cmd.extend(['--extractor-args', f'youtube:player-skip=js,po_token={po_token}'])
    
    # Download the video and convert to MP3
    ytdl_log(f"Downloading video: {video_title} ({video_id})")
    
    # Run the download command with real-time output
    return_code, stdout, stderr = run_subprocess_with_realtime_output(
        ytdl_cmd + [video_path],
        ytdl_log,
        "YTDL"
    )
    
    # Check if the download was successful
    if not os.path.exists(mp3_path) and return_code != 0:
        # If download failed, try with cookies if available
        ytdl_log("Initial download failed. Trying with cookies if available...")
        cookies_path = os.path.expanduser("~/.config/yt-dlp/cookies.txt")
        
        if os.path.exists(cookies_path):
            ytdl_log("Found cookies file, retrying with cookies...")
            ytdl_cmd.extend(['--cookies', cookies_path])
            
            return_code, stdout, stderr = run_subprocess_with_realtime_output(
                ytdl_cmd + [video_path],
                ytdl_log,
                "YTDL (with cookies)"
            )
    
    # Check if the file exists now (after download attempts)
    if os.path.exists(mp3_path):
        ytdl_log(f"Successfully downloaded: {mp3_path}")
        return mp3_path
    else:
        # If still failed, raise exception
        raise Exception(
            f"Error encountered running youtube-dl. mp3_path not found after youtube-dl: {mp3_path}. Return code: {return_code}. Stderr follows: {stderr}")
