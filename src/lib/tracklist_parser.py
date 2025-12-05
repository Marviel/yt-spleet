"""
Tracklist parser using LLM to extract track information from YouTube comments.
"""
import os
import re
import json
import subprocess
import tempfile
from typing import Optional
from dataclasses import dataclass


@dataclass
class Track:
    """A single track in a tracklist."""
    number: int
    title: str
    artist: Optional[str]
    start_time: str  # Format: "HH:MM:SS" or "MM:SS"
    start_seconds: int


@dataclass 
class Tracklist:
    """Parsed tracklist from a comment."""
    tracks: list[Track]


def extract_comment_id_from_url(url: str) -> Optional[str]:
    """
    Extract the comment ID from a YouTube URL.
    
    YouTube comment links use the `lc=` parameter.
    Example: https://www.youtube.com/watch?v=VIDEO_ID&lc=COMMENT_ID
    
    Returns:
        Comment ID string or None if not found
    """
    match = re.search(r'[?&]lc=([^&]+)', url)
    if match:
        return match.group(1)
    return None


def fetch_youtube_comment_via_ytdlp(url: str, comment_id: Optional[str] = None) -> str:
    """
    Fetch YouTube comment(s) using yt-dlp.
    
    Args:
        url: YouTube video URL
        comment_id: Optional specific comment ID to find (from lc= parameter)
        
    Returns:
        The comment text content
    """
    print(f"Fetching comments via yt-dlp...")
    
    # Use yt-dlp to get video info with comments
    cmd = [
        'yt-dlp',
        '--write-comments',
        '--skip-download',
        '--dump-json',
        url
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        
        comments = data.get('comments', [])
        if not comments:
            raise ValueError("No comments found on this video")
        
        print(f"Found {len(comments)} comments")
        
        # If we have a specific comment ID, find it
        if comment_id:
            for comment in comments:
                if comment.get('id') == comment_id:
                    return comment.get('text', '')
            
            # Comment ID not found - maybe it's a reply, check all
            print(f"Comment ID {comment_id} not found in top-level comments, checking all...")
            # The comment might be formatted differently, try partial match
            for comment in comments:
                cid = comment.get('id', '')
                if comment_id in cid or cid in comment_id:
                    return comment.get('text', '')
            
            raise ValueError(f"Comment {comment_id} not found in video comments")
        
        # No specific ID - return the first comment (usually pinned/top)
        # Or we could return all comments and let the LLM figure it out
        # For tracklists, they're often pinned or in the first few comments
        
        # Look for a comment that looks like a tracklist (has timestamps)
        for comment in comments[:20]:  # Check first 20 comments
            text = comment.get('text', '')
            # Look for timestamp patterns like "0:00" or "1:23:45"
            if re.search(r'\d+:\d{2}', text):
                print(f"Found tracklist-like comment")
                return text
        
        # Fallback to first comment
        return comments[0].get('text', '')
        
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to fetch comments: {e.stderr}")


def parse_timestamp_to_seconds(timestamp: str) -> int:
    """
    Convert a timestamp string to total seconds.
    
    Handles formats:
    - "0:00" -> 0
    - "1:30" -> 90
    - "1:23:45" -> 5025
    
    Args:
        timestamp: Time string in MM:SS or H:MM:SS format
        
    Returns:
        Total seconds as integer, or -1 if parsing fails
    """
    if not timestamp:
        return -1
    
    try:
        parts = timestamp.split(':')
        if len(parts) == 2:
            # MM:SS format
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            # H:MM:SS format
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        else:
            return -1
    except (ValueError, IndexError):
        return -1


def parse_tracklist_with_llm(comment_text: str, model: str = "gpt-5-mini") -> Tracklist:
    """
    Use LiteLLM to parse a tracklist from comment text.
    
    Args:
        comment_text: Raw comment text containing the tracklist
        model: LLM model to use (default: gpt-5-mini)
        
    Returns:
        Parsed Tracklist object
    """
    try:
        from litellm import completion
    except ImportError:
        raise ImportError("litellm is required for --guess-chapters. Install with: pip install litellm")
    
    # Note: We only ask for start_time, we compute start_seconds ourselves
    # because LLMs are bad at math!
    system_prompt = """You are a tracklist parser. Given a comment containing a tracklist/setlist, extract all tracks with their timestamps.

Return a JSON object with this exact structure:
{
  "tracks": [
    {
      "number": 1,
      "title": "Track Title",
      "artist": "Artist Name or null if not specified",
      "start_time": "0:00"
    }
  ]
}

Rules:
- Keep start_time EXACTLY as written in the comment (e.g. "1:23:45" or "45:30")
- If artist is combined with title (e.g. "Artist - Title"), split them
- If only title is given, set artist to null
- Include ALL tracks, even if some say "Unreleased" or "ID"
- If a track has no timestamp, use null for start_time
- Return ONLY valid JSON, no markdown or explanation"""

    user_prompt = f"""Parse this tracklist comment:

{comment_text}"""

    response = completion(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"}
    )
    
    result_text = response.choices[0].message.content
    result = json.loads(result_text)
    
    tracks = []
    for t in result.get('tracks', []):
        start_time = t.get('start_time', '0:00')
        # Compute start_seconds ourselves - don't trust LLM math!
        start_seconds = parse_timestamp_to_seconds(start_time) if start_time else -1
        
        tracks.append(Track(
            number=t.get('number', 0),
            title=t.get('title', 'Unknown'),
            artist=t.get('artist'),
            start_time=start_time or '0:00',
            start_seconds=start_seconds
        ))
    
    return Tracklist(tracks=tracks)


def parse_tracklist_from_url(url: str, model: str = "gpt-5-mini") -> Tracklist:
    """
    Extract and parse a tracklist from a YouTube comment URL.
    
    Args:
        url: YouTube URL (optionally with lc= comment parameter)
        model: LLM model to use
        
    Returns:
        Parsed Tracklist object
    """
    comment_id = extract_comment_id_from_url(url)
    
    print(f"Fetching comments from video...")
    if comment_id:
        print(f"Looking for specific comment: {comment_id}")
    
    comment_text = fetch_youtube_comment_via_ytdlp(url, comment_id)
    print(f"Comment text:\n{comment_text}\n")
    
    print(f"Parsing tracklist with {model}...")
    tracklist = parse_tracklist_with_llm(comment_text, model)
    print(f"Found {len(tracklist.tracks)} tracks")
    
    return tracklist

