#!/usr/bin/env python3
"""Run AI content moderation on video"""

import argparse
import os
import sys
import json
import asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add scripts to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.fast_video_processor import FastAIModerator, ModerationResult

async def run_moderation(kosher_flag: bool = False):
    """Run content moderation"""
    
    video_path = "/tmp/videos/video.mp4"
    audio_path = "/tmp/videos/audio.wav"
    thumbnail_path = "/tmp/videos/thumbnail.webp"
    
    # Find actual files
    for f in Path("/tmp/videos").glob("*.mp4"):
        video_path = str(f)
        break
    
    for f in Path("/tmp/videos").glob("*.wav"):
        audio_path = str(f)
        break
    
    for f in Path("/tmp/videos").glob("*.webp"):
        thumbnail_path = str(f)
        break
    
    if kosher_flag:
        logger.info("✓ Kosher flag set - skipping content check")
        result = ModerationResult(approved=True)
    else:
        logger.info("🤖 Starting AI content analysis...")
        
        moderator = FastAIModerator()
        result = await moderator.analyze_content(video_path, audio_path, thumbnail_path)
    
    # Write outputs for GitHub Actions
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"approved={str(result.approved).lower()}\n")
            f.write(f"rejection_reason={result.rejection_reason}\n")
            f.write(f"blur_regions={json.dumps(result.blur_regions or [])}\n")
            f.write(f"audio_cuts={json.dumps(result.audio_cuts or [])}\n")
            f.write(f"needs_manual_review={str(result.needs_manual_review).lower()}\n")
    
    if result.approved:
        logger.info("✓ Content approved")
    else:
        logger.warning(f"❌ Content rejected: {result.rejection_reason}")
    
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--kosher-flag", default="false")
    args = parser.parse_args()
    
    kosher_flag = args.kosher_flag.lower() == "true"
    asyncio.run(run_moderation(kosher_flag))
