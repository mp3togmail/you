#!/usr/bin/env python3
"""Process video - blur, cut audio, extract formats"""

import argparse
import os
import sys
import json
import asyncio
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.fast_video_processor import FastVideoProcessor, ModerationResult

async def process_video(requested_format: str = "both", output_dir: str = "/tmp/videos/processed"):
    """Process video based on moderation results"""
    
    # Find files
    video_path = None
    audio_path = None
    
    for f in Path("/tmp/videos").glob("*.mp4"):
        video_path = str(f)
        break
    
    for f in Path("/tmp/videos").glob("*.wav"):
        audio_path = str(f)
        break
    
    if not video_path or not audio_path:
        logger.error("❌ Video or audio file not found")
        return
    
    logger.info(f"🎬 Processing video (format: {requested_format})")
    
    # Load moderation result if exists
    blur_regions = []
    audio_cuts = []
    
    if os.path.exists("/tmp/videos/moderation_result.json"):
        with open("/tmp/videos/moderation_result.json") as f:
            mod_data = json.load(f)
            blur_regions = mod_data.get("blur_regions", [])
            audio_cuts = mod_data.get("audio_cuts", [])
    
    moderation_result = ModerationResult(
        approved=True,
        blur_regions=blur_regions,
        audio_cuts=audio_cuts
    )
    
    # Process video
    processor = FastVideoProcessor()
    results = await processor.process(
        video_path, audio_path, moderation_result,
        requested_format, output_dir
    )
    
    # Write outputs for GitHub Actions
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            for fmt, path in results.items():
                f.write(f"{fmt}_path={path}\n")
    
    logger.info(f"✓ Processing complete")
    return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", default="both")
    parser.add_argument("--output-dir", default="/tmp/videos/processed")
    args = parser.parse_args()
    
    asyncio.run(process_video(args.format, args.output_dir))
