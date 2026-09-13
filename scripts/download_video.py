#!/usr/bin/env python3
"""Download YouTube video and extract audio"""

import argparse
import os
import sys
import json
import subprocess
from pathlib import Path
from yt_dlp import YoutubeDL
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_video(url: str, output_dir: str) -> dict:
    """Download video and extract audio"""
    
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    ydl_opts = {
        'format': 'worst[ext=mp4]',
        'quiet': True,
        'no_warnings': True,
        'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'),
        'writethumbnail': True,
        'writeinfojson': True,
    }
    
    logger.info(f"⬇️ Downloading: {url}")
    
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        video_id = info['id']
        video_file = os.path.join(output_dir, f"{video_id}.mp4")
        
        # Extract audio
        audio_file = os.path.join(output_dir, "audio.wav")
        subprocess.run([
            'ffmpeg', '-i', video_file,
            '-q:a', '9', '-n',
            '-f', 'wav', audio_file
        ], capture_output=True, timeout=300)
        
        result = {
            "video_path": video_file,
            "audio_path": audio_file,
            "thumbnail": os.path.join(output_dir, f"{video_id}.webp"),
            "title": info.get('title', 'Unknown'),
            "description": info.get('description', '')[:500],
            "duration": info.get('duration', 0),
        }
        
        # Write outputs for GitHub Actions
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                for key, value in result.items():
                    f.write(f"{key}={value}\n")
        
        logger.info(f"✓ Download complete")
        return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    
    download_video(args.url, args.output_dir)
