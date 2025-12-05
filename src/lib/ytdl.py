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


def get_playlist_video_urls(url: str) -> list[str]:
    """
    Extract all video URLs from a YouTube playlist URL.
    
    Args:
        url: YouTube URL (may contain a playlist parameter)
        
    Returns:
        List of individual video URLs from the playlist
    """
    ytdl_log(f"Extracting playlist videos from: {url}")
    
    # Use yt-dlp to get playlist info as JSON
    cmd = [
        'yt-dlp',
        '--flat-playlist',  # Don't download, just get info
        '--dump-json',      # Output JSON for each video
        url
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        video_urls = []
        # Each line is a separate JSON object for each video in the playlist
        for line in result.stdout.strip().split('\n'):
            if line:
                video_info = json.loads(line)
                video_id = video_info.get('id')
                if video_id:
                    video_urls.append(f"https://www.youtube.com/watch?v={video_id}")
        
        ytdl_log(f"Found {len(video_urls)} videos in playlist")
        return video_urls
        
    except subprocess.CalledProcessError as e:
        ytdl_log(f"Error extracting playlist: {e.stderr}")
        raise Exception(f"Failed to extract playlist videos: {e.stderr}")


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


def run_ytdl(video_path: str, po_token: Optional[str] = None, output_folder: Optional[str] = None, split_chapters: bool = False, time_range: Optional[Tuple[str, str]] = None) -> str:
    """
    Run youtube-dl to download a video and convert it to MP3.
    
    Args:
        video_path: YouTube URL to download
        po_token: Optional PO token to use for authentication
        output_folder: Optional custom output folder path (overrides default)
        split_chapters: Split video into separate files by chapter
        time_range: Optional tuple of (start_time, end_time) in HH:MM:SS format
        
    Returns:
        Path to the downloaded MP3 file (or output directory if split_chapters is True)
    """
    # Extract video ID and get title
    video_id = get_video_id(video_path)
    video_title = get_video_title(video_id)
    
    # Create a clean filename with title and ID
    clean_filename = f"{video_title}-{video_id}"
    
    # Add time range suffix if specified (so it doesn't conflict with full video)
    if time_range:
        # Convert HH:MM:SS to compact format like "01h09m19s"
        def compact_time(t: str) -> str:
            parts = t.split(':')
            return f"{parts[0]}h{parts[1]}m{parts[2]}s"
        time_suffix = f"_{compact_time(time_range[0])}-{compact_time(time_range[1])}"
        file_basename = f"{clean_filename}{time_suffix}"
    else:
        file_basename = clean_filename
    
    # Use custom output folder if provided, otherwise use default
    base_output_folder = output_folder if output_folder else YTSPLEET_DEFAULT_OUTPUT_FOLDER
    
    # Create output directory structure (use clean_filename for folder, not time-suffixed)
    output_dir = os.path.join(base_output_folder, clean_filename)
    os.makedirs(output_dir, exist_ok=True)
    
    # Define the output template based on whether we're splitting chapters
    if split_chapters:
        # For chapter splits, use chapter: prefix to control output location
        # The temp file goes to output_dir, and chapter files use section_title
        temp_template = os.path.join(output_dir, f"{file_basename}.%(ext)s")
        chapter_template = os.path.join(output_dir, f"%(section_number)03d - %(section_title)s.%(ext)s")
        mp3_path = output_dir  # Return directory when splitting chapters
    else:
        output_template = os.path.join(output_dir, f"{file_basename}.%(ext)s")
        mp3_path = os.path.join(output_dir, f"{file_basename}.mp3")
        mp3_path = os.path.abspath(mp3_path)
        
        # If the file already exists, return its path
        if os.path.exists(mp3_path):
            ytdl_log(f"File already exists: {mp3_path}")
            return mp3_path
    
    # Base command with alternative clients to avoid DRM issues
    ytdl_cmd = [
        'yt-dlp',
        '-x',
        '--audio-format', 'mp3',
        '--extractor-args',
        'youtube:player-client=default,-tv,web_safari,web_embedded',  # Use alternative clients, avoid TV client
    ]
    
    # Add output template(s)
    if split_chapters:
        ytdl_cmd.extend(['-o', temp_template])
        ytdl_cmd.extend(['-o', f'chapter:{chapter_template}'])
        ytdl_cmd.append('--split-chapters')
    else:
        ytdl_cmd.extend(['-o', output_template])
    
    # Add time range extraction if specified
    if time_range:
        start_time, end_time = time_range
        ytdl_cmd.extend(['--download-sections', f'*{start_time}-{end_time}'])
    
    # Add PO token if provided
    if po_token:
        ytdl_cmd.extend(['--extractor-args', f'youtube:player-skip=js,po_token={po_token}'])
    
    # Download the video and convert to MP3
    ytdl_log(f"Downloading video: {video_title} ({video_id})")
    if time_range:
        ytdl_log(f"Extracting section: {time_range[0]} to {time_range[1]}")
    if split_chapters:
        ytdl_log("Splitting by chapters...")
    
    # Run the download command with real-time output
    return_code, stdout, stderr = run_subprocess_with_realtime_output(
        ytdl_cmd + [video_path],
        ytdl_log,
        "YTDL"
    )
    
    # Check if the download was successful
    if split_chapters:
        # For chapter splits, check if any mp3 files were created in the output directory
        mp3_files = glob.glob(os.path.join(output_dir, "*.mp3"))
        if not mp3_files and return_code != 0:
            # Try with cookies
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
                mp3_files = glob.glob(os.path.join(output_dir, "*.mp3"))
        
        if mp3_files:
            ytdl_log(f"Successfully downloaded {len(mp3_files)} chapter(s) to: {output_dir}")
            return output_dir
        else:
            raise Exception(
                f"Error encountered running youtube-dl. No mp3 files found in {output_dir}. Return code: {return_code}. Stderr follows: {stderr}")
    else:
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
