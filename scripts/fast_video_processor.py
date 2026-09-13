"""
Fast AI-Powered Video Processor
Processes video with parallel AI analysis and video editing
Optimized for speed: ~8-12 minutes total
"""

import os
import sys
import json
import asyncio
import logging
from typing import Dict, List, Any, Tuple
from pathlib import Path
from dataclasses import dataclass
import subprocess
import tempfile
import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# AI and video libraries
import cv2
import numpy as np
from yt_dlp import YoutubeDL
import librosa
import soundfile as sf
from openai import AsyncOpenAI
import ffmpeg

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class ModerationResult:
    approved: bool
    rejection_reason: str = ""
    blur_regions: List[Dict] = None
    audio_cuts: List[Tuple[float, float]] = None
    summary: str = ""
    needs_manual_review: bool = False

class FastVideoDownloader:
    """Download YouTube video efficiently"""
    
    @staticmethod
    async def download(url: str, output_dir: str, low_res: bool = True) -> Dict[str, str]:
        """
        Download YouTube video
        Returns: {video_path, audio_path, thumbnail, metadata}
        """
        logger.info(f"⬇️  Downloading video from {url}")
        
        ydl_opts = {
            'format': 'worst[ext=mp4]' if low_res else 'best[ext=mp4]',
            'quiet': True,
            'no_warnings': True,
            'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'),
            'writethumbnail': True,
            'writeinfojson': True,
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info['id']
            video_file = os.path.join(output_dir, f"{video_id}.mp4")
            thumbnail_file = os.path.join(output_dir, f"{video_id}.webp")
            
            # Extract audio
            audio_path = await FastVideoDownloader._extract_audio(video_file, output_dir)
            
            logger.info(f"✓ Download complete: {video_file}")
            
            return {
                "video_path": video_file,
                "audio_path": audio_path,
                "thumbnail": thumbnail_file,
                "title": info.get('title', 'Unknown'),
                "description": info.get('description', ''),
                "duration": info.get('duration', 0),
            }
    
    @staticmethod
    async def _extract_audio(video_path: str, output_dir: str) -> str:
        """Extract audio from video"""
        audio_path = os.path.join(output_dir, "audio.wav")
        
        cmd = [
            'ffmpeg', '-i', video_path,
            '-q:a', '9', '-n',
            '-f', 'wav', audio_path
        ]
        
        subprocess.run(cmd, capture_output=True, timeout=300)
        return audio_path


class FastAIModerator:
    """Fast AI content moderation using OpenAI Vision & Audio"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.max_frames = 10  # Sample 10 frames for speed
    
    async def analyze_content(
        self,
        video_path: str,
        audio_path: str,
        thumbnail_path: str
    ) -> ModerationResult:
        """
        Parallel analysis of video frames, audio, and thumbnail
        Fast mode: sample frames instead of full analysis
        """
        logger.info("🤖 Starting AI content analysis")
        
        try:
            # Run analyses in parallel
            frame_analysis, audio_analysis = await asyncio.gather(
                self._analyze_video_frames(video_path),
                self._analyze_audio(audio_path),
                return_exceptions=True
            )
            
            # Combine results
            is_approved = (
                frame_analysis.get("approved", False) and
                audio_analysis.get("approved", False)
            )
            
            blur_regions = frame_analysis.get("blur_regions", [])
            audio_cuts = audio_analysis.get("cuts", [])
            
            rejection_reasons = []
            if not frame_analysis.get("approved"):
                rejection_reasons.append(frame_analysis.get("reason", "Inappropriate video content"))
            if not audio_analysis.get("approved"):
                rejection_reasons.append(audio_analysis.get("reason", "Inappropriate audio content"))
            
            result = ModerationResult(
                approved=is_approved,
                rejection_reason=" | ".join(rejection_reasons) if rejection_reasons else "",
                blur_regions=blur_regions,
                audio_cuts=audio_cuts,
                summary=f"Frames: {frame_analysis.get('summary', '')} | Audio: {audio_analysis.get('summary', '')}",
                needs_manual_review=(
                    frame_analysis.get("manual_review", False) or
                    audio_analysis.get("manual_review", False)
                )
            )
            
            logger.info(f"✓ Analysis complete - Approved: {is_approved}")
            return result
            
        except Exception as e:
            logger.error(f"AI analysis error: {str(e)}")
            return ModerationResult(
                approved=False,
                rejection_reason=f"Analysis error: {str(e)}",
                needs_manual_review=True
            )
    
    async def _analyze_video_frames(self, video_path: str) -> Dict[str, Any]:
        """
        Sample key frames from video and analyze for:
        - Adult content
        - Inappropriate clothing/imagery
        - Nudity
        """
        logger.info("📹 Analyzing video frames")
        
        frames = await self._sample_frames(video_path, self.max_frames)
        
        if not frames:
            return {"approved": False, "reason": "Could not extract frames"}
        
        # Prepare frames for API
        frame_messages = []
        for idx, frame_base64 in enumerate(frames):
            frame_messages.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{frame_base64}",
                    "detail": "low"  # Low detail for speed
                }
            })
        
        # Single API call for all frames
        try:
            response = await self.client.messages.create(
                model="gpt-4-vision",
                max_tokens=500,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """Analyze these video frames. Check for:
1. Adult/pornographic content
2. Inappropriate nudity or suggestive imagery
3. People dressed inappropriately (revealing clothing, bikinis, etc.)
4. Any content unsuitable for religious Orthodox Jewish youth

Respond in JSON format:
{
    "approved": true/false,
    "reason": "specific reason if rejected",
    "manual_review": true/false,
    "blur_regions": [{"frame": 0, "region": "area description", "confidence": 0.9}],
    "summary": "brief summary"
}"""
                            },
                            *frame_messages
                        ]
                    }
                ]
            )
            
            result = json.loads(response.content[0].text)
            return result
            
        except Exception as e:
            logger.error(f"Frame analysis error: {str(e)}")
            return {
                "approved": False,
                "reason": f"Frame analysis failed: {str(e)}",
                "manual_review": True
            }
    
    async def _analyze_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        Analyze audio for:
        - Adult/sexual content in speech
        - Profanity
        - Inappropriate topics
        """
        logger.info("🔊 Analyzing audio")
        
        try:
            # Transcribe audio with OpenAI Whisper
            with open(audio_path, "rb") as audio_file:
                transcript_response = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            
            transcript = transcript_response.text
            logger.info(f"📝 Transcribed: {transcript[:100]}...")
            
            # Analyze transcript for inappropriate content
            moderation_response = await self.client.moderations.create(
                input=transcript
            )
            
            # Check for flagged content
            flagged = moderation_response.results[0].flagged
            categories = moderation_response.results[0].category_scores
            
            # Check specific categories
            adult_score = categories.get("sexual", 0)
            explicit_score = categories.get("sexual/explicit", 0)
            
            if flagged or adult_score > 0.7 or explicit_score > 0.7:
                # Find timestamps of inappropriate content
                cuts = await self._find_inappropriate_segments(transcript, audio_path)
                
                return {
                    "approved": False,
                    "reason": "Audio contains inappropriate content",
                    "cuts": cuts,
                    "manual_review": False,
                    "summary": f"Detected inappropriate speech (score: {max(adult_score, explicit_score):.2f})"
                }
            
            return {
                "approved": True,
                "cuts": [],
                "manual_review": False,
                "summary": "Audio is appropriate"
            }
            
        except Exception as e:
            logger.error(f"Audio analysis error: {str(e)}")
            return {
                "approved": False,
                "reason": f"Audio analysis failed",
                "manual_review": True
            }
    
    async def _find_inappropriate_segments(
        self,
        transcript: str,
        audio_path: str
    ) -> List[Tuple[float, float]]:
        """Find timestamps of inappropriate segments in audio"""
        # This is simplified - in production you'd need more sophisticated segmentation
        # For now, return empty (keep audio) to avoid over-cutting
        return []
    
    async def _sample_frames(self, video_path: str, num_frames: int) -> List[str]:
        """Sample frames from video and convert to base64"""
        import base64
        import cv2
        
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        frame_indices = np.linspace(0, total_frames - 1, num_frames, dtype=int)
        
        frames_b64 = []
        
        for frame_idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            
            if ret:
                # Resize for speed and API limits
                frame = cv2.resize(frame, (640, 480))
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                frame_b64 = base64.b64encode(buffer).decode()
                frames_b64.append(frame_b64)
        
        cap.release()
        return frames_b64


class FastVideoProcessor:
    """Process video: blur, cut audio, extract formats"""
    
    @staticmethod
    async def process(
        video_path: str,
        audio_path: str,
        moderation_result: ModerationResult,
        requested_format: str = "both",
        output_dir: str = "./processed"
    ) -> Dict[str, str]:
        """
        Process video based on moderation results
        Returns paths to MP3 and/or MP4
        """
        logger.info(f"🎬 Processing video (format: {requested_format})")
        
        os.makedirs(output_dir, exist_ok=True)
        
        tasks = []
        results = {}
        
        # Process based on format request
        if requested_format in ["mp4", "both"]:
            tasks.append(
                FastVideoProcessor._process_mp4(
                    video_path, moderation_result, output_dir
                )
            )
        
        if requested_format in ["mp3", "both"]:
            tasks.append(
                FastVideoProcessor._process_mp3(
                    audio_path, moderation_result, output_dir
                )
            )
        
        # Run processing in parallel
        processed_files = await asyncio.gather(*tasks, return_exceptions=True)
        
        for idx, file_path in enumerate(processed_files):
            if isinstance(file_path, str):
                format_type = "mp4" if idx == 0 else "mp3"
                results[format_type] = file_path
                logger.info(f"✓ {format_type.upper()} ready: {file_path}")
        
        return results
    
    @staticmethod
    async def _process_mp4(
        video_path: str,
        moderation_result: ModerationResult,
        output_dir: str
    ) -> str:
        """Process and blur video"""
        logger.info("Processing MP4...")
        output_path = os.path.join(output_dir, "output.mp4")
        
        # If no blur regions, just copy
        if not moderation_result.blur_regions:
            shutil.copy(video_path, output_path)
            return output_path
        
        # Apply blur to regions
        cap = cv2.VideoCapture(video_path)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Apply blur to regions for this frame
            for region in moderation_result.blur_regions:
                if region.get("frame") == frame_idx or "frame" not in region:
                    # Extract region coordinates and blur
                    x, y, w, h = region.get("bbox", [0, 0, width, height])
                    frame[y:y+h, x:x+w] = cv2.blur(frame[y:y+h, x:x+w], (51, 51))
            
            out.write(frame)
            frame_idx += 1
        
        cap.release()
        out.release()
        
        logger.info(f"✓ MP4 blurred and saved")
        return output_path
    
    @staticmethod
    async def _process_mp3(
        audio_path: str,
        moderation_result: ModerationResult,
        output_dir: str
    ) -> str:
        """Extract and process audio"""
        logger.info("Processing MP3...")
        output_path = os.path.join(output_dir, "output.mp3")
        
        # Load audio
        y, sr = librosa.load(audio_path, sr=44100)
        
        # Remove inappropriate segments if any
        if moderation_result.audio_cuts:
            for start, end in moderation_result.audio_cuts:
                start_sample = int(start * sr)
                end_sample = int(end * sr)
                y[start_sample:end_sample] = 0  # Silence the segment
        
        # Save as MP3
        sf.write(output_path, y, sr)
        
        logger.info(f"✓ MP3 saved")
        return output_path


class FastEmailSender:
    """Send processed video via email"""
    
    @staticmethod
    async def send_success_email(
        recipient: str,
        video_title: str,
        video_description: str,
        thumbnail_url: str,
        google_drive_link: str,
        download_link: str
    ):
        """Send success email with download links"""
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        sender_email = os.getenv("GMAIL_SENDER_EMAIL")
        sender_password = os.getenv("GMAIL_APP_PASSWORD")
        
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; background-color: #f5f5f5;">
                <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 10px;">
                    <h2 style="color: #333;">✓ Your Video is Ready!</h2>
                    
                    <div style="text-align: center; margin: 20px 0;">
                        <img src="{thumbnail_url}" style="max-width: 100%; border-radius: 5px;" alt="Video thumbnail">
                    </div>
                    
                    <h3 style="color: #2c3e50;">{video_title}</h3>
                    <p style="color: #666; font-size: 14px;">{video_description[:300]}...</p>
                    
                    <div style="background-color: #f0f0f0; padding: 15px; border-radius: 5px; margin: 20px 0;">
                        <p><strong>Download Options:</strong></p>
                        <a href="{download_link}" style="display: inline-block; background-color: #4CAF50; color: white; padding: 10px 20px; margin: 5px; text-decoration: none; border-radius: 5px;">
                            📥 Direct Download
                        </a>
                        <a href="{google_drive_link}" style="display: inline-block; background-color: #2196F3; color: white; padding: 10px 20px; margin: 5px; text-decoration: none; border-radius: 5px;">
                            ☁️ Google Drive
                        </a>
                    </div>
                    
                    <p style="color: #999; font-size: 12px; text-align: center; margin-top: 30px;">
                        This video has been checked and approved by our kosher content filter.
                    </p>
                </div>
            </body>
        </html>
        """
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"✓ Your Video: {video_title}"
            msg["From"] = sender_email
            msg["To"] = recipient
            
            msg.attach(MIMEText(html_content, "html"))
            
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipient, msg.as_string())
            
            logger.info(f"✓ Success email sent to {recipient}")
            
        except Exception as e:
            logger.error(f"Email sending error: {str(e)}")


async def main():
    """Main processing pipeline"""
    
    # Get environment variables
    email_data = json.loads(os.getenv("EMAIL_DATA", "{}"))
    youtube_url = email_data.get("youtube_url")
    sender_email = email_data.get("sender_email")
    requested_format = email_data.get("requested_format", "both")
    kosher_flag = email_data.get("kosher_flag", False)
    
    logger.info(f"🎯 Processing video from {sender_email}")
    logger.info(f"📺 URL: {youtube_url}")
    
    temp_dir = tempfile.mkdtemp(prefix="video_")
    output_dir = os.path.join(temp_dir, "processed")
    
    try:
        # Step 1: Download video
        downloader = FastVideoDownloader()
        download_result = await downloader.download(youtube_url, temp_dir, low_res=True)
        
        logger.info(f"⏱️  Elapsed: Download complete ({datetime.now()})")
        
        # Step 2: AI Moderation (unless kosher flag)
        if kosher_flag:
            logger.info("✓ Kosher flag set - skipping content check")
            moderation_result = ModerationResult(approved=True)
        else:
            moderator = FastAIModerator()
            moderation_result = await moderator.analyze_content(
                download_result["video_path"],
                download_result["audio_path"],
                download_result["thumbnail"]
            )
        
        logger.info(f"⏱️  Elapsed: Moderation complete ({datetime.now()})")
        
        # Step 3: Check approval
        if not moderation_result.approved:
            logger.warning(f"❌ Video rejected: {moderation_result.rejection_reason}")
            # Send rejection email
            await FastEmailSender.send_rejection_email(
                sender_email,
                moderation_result.rejection_reason
            )
            return
        
        # Step 4: Process video
        processor = FastVideoProcessor()
        processed_files = await processor.process(
            download_result["video_path"],
            download_result["audio_path"],
            moderation_result,
            requested_format,
            output_dir
        )
        
        logger.info(f"⏱️  Elapsed: Video processing complete ({datetime.now()})")
        
        # Step 5: Upload to Google Drive
        # (Implementation in next file)
        
        logger.info("✓ All processing complete!")
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(main())
