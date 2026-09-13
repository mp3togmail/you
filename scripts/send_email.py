#!/usr/bin/env python3
"""Send formatted HTML emails with download links"""

import os
import sys
import json
import argparse
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailSender:
    def __init__(self):
        """Initialize email sender"""
        self.sender_email = os.getenv("GMAIL_SENDER_EMAIL")
        self.sender_password = os.getenv("GMAIL_APP_PASSWORD")
        
        if not self.sender_email or not self.sender_password:
            logger.error("❌ GMAIL_SENDER_EMAIL or GMAIL_APP_PASSWORD not set")
    
    def send_success_email(self, recipient: str, video_data: dict, drive_links: dict):
        """Send success email with download links"""
        
        logger.info(f"📧 Sending success email to {recipient}")
        
        video_title = video_data.get('title', 'Unknown')
        video_description = video_data.get('description', '')[:300]
        
        # Build download buttons
        download_buttons = ""
        
        if 'mp4' in drive_links:
            mp4_link = drive_links['mp4'].get('link', '')
            if mp4_link:
                download_buttons += f'''
                <a href="{mp4_link}" style="display: inline-block; background-color: #4CAF50; color: white; padding: 12px 24px; margin: 8px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px;">
                    📥 Download MP4
                </a>
                '''
        
        if 'mp3' in drive_links:
            mp3_link = drive_links['mp3'].get('link', '')
            if mp3_link:
                download_buttons += f'''
                <a href="{mp3_link}" style="display: inline-block; background-color: #2196F3; color: white; padding: 12px 24px; margin: 8px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px;">
                    📥 Download MP3
                </a>
                '''
        
        # Get thumbnail if available
        thumbnail_html = ""
        thumbnail_path = "/tmp/videos/thumbnail.webp"
        for f in Path("/tmp/videos").glob("*.webp"):
            thumbnail_path = str(f)
            break
        
        if os.path.exists(thumbnail_path):
            thumbnail_html = f'<img src="cid:thumbnail" style="max-width: 100%; border-radius: 8px; margin-bottom: 20px;" alt="Video thumbnail">'
        
        html_content = f"""
        <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background-color: #f5f5f5;
                        margin: 0;
                        padding: 0;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        background-color: white;
                        padding: 30px;
                        border-radius: 10px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    }}
                    .header {{
                        text-align: center;
                        margin-bottom: 30px;
                    }}
                    .header h2 {{
                        color: #4CAF50;
                        font-size: 28px;
                        margin: 0;
                    }}
                    .title {{
                        color: #2c3e50;
                        font-size: 24px;
                        font-weight: bold;
                        margin: 20px 0;
                    }}
                    .description {{
                        color: #666;
                        font-size: 14px;
                        line-height: 1.6;
                        margin: 15px 0;
                    }}
                    .downloads {{
                        background-color: #f9f9f9;
                        padding: 20px;
                        border-radius: 8px;
                        margin: 20px 0;
                        border-left: 4px solid #4CAF50;
                    }}
                    .downloads-title {{
                        font-weight: bold;
                        color: #333;
                        margin-bottom: 15px;
                        font-size: 16px;
                    }}
                    .footer {{
                        text-align: center;
                        color: #999;
                        font-size: 12px;
                        margin-top: 30px;
                        padding-top: 20px;
                        border-top: 1px solid #eee;
                    }}
                    .kosher-badge {{
                        display: inline-block;
                        background-color: #4CAF50;
                        color: white;
                        padding: 5px 10px;
                        border-radius: 3px;
                        font-size: 12px;
                        font-weight: bold;
                        margin: 10px 0;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>✓ Your Video is Ready!</h2>
                    </div>
                    
                    <div style="text-align: center;">
                        {thumbnail_html}
                    </div>
                    
                    <div class="title">{video_title}</div>
                    
                    <div class="description">
                        {video_description}
                    </div>
                    
                    <div class="downloads">
                        <div class="downloads-title">📥 Download Options:</div>
                        <div style="text-align: center;">
                            {download_buttons}
                        </div>
                    </div>
                    
                    <div style="text-align: center;">
                        <span class="kosher-badge">✓ KOSHER APPROVED</span>
                    </div>
                    
                    <div class="footer">
                        <p>This video has been reviewed and approved by our AI content moderation system.</p>
                        <p>Files will be automatically deleted after 2 days.</p>
                        <p style="margin-top: 15px; font-size: 11px;">
                            <strong>Notice:</strong> Please download your files promptly as they are temporary and will be removed for privacy.
                        </p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"✓ Your Video: {video_title}"
            msg["From"] = self.sender_email
            msg["To"] = recipient
            
            msg.attach(MIMEText(html_content, "html"))
            
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, recipient, msg.as_string())
            
            logger.info(f"✓ Success email sent to {recipient}")
            
        except Exception as e:
            logger.error(f"❌ Error sending email: {str(e)}")
    
    def send_rejection_email(self, recipient: str, rejection_reason: str):
        """Send rejection email"""
        
        logger.info(f"📧 Sending rejection email to {recipient}")
        
        html_content = f"""
        <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background-color: #f5f5f5;
                        margin: 0;
                        padding: 0;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        background-color: white;
                        padding: 30px;
                        border-radius: 10px;
                        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    }}
                    .header {{
                        text-align: center;
                        margin-bottom: 30px;
                    }}
                    .header h2 {{
                        color: #d32f2f;
                        font-size: 28px;
                        margin: 0;
                    }}
                    .reason-box {{
                        background-color: #ffebee;
                        padding: 20px;
                        border-radius: 8px;
                        border-left: 4px solid #d32f2f;
                        margin: 20px 0;
                    }}
                    .reason-box p {{
                        color: #c62828;
                        margin: 0;
                        font-weight: 500;
                    }}
                    .footer {{
                        text-align: center;
                        color: #999;
                        font-size: 12px;
                        margin-top: 30px;
                        padding-top: 20px;
                        border-top: 1px solid #eee;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>❌ Video Not Approved</h2>
                    </div>
                    
                    <p style="color: #666; font-size: 16px;">
                        Unfortunately, the video you requested could not be processed and approved.
                    </p>
                    
                    <div class="reason-box">
                        <p><strong>Reason:</strong></p>
                        <p>{rejection_reason}</p>
                    </div>
                    
                    <p style="color: #666; font-size: 14px; line-height: 1.6;">
                        Our system uses advanced AI technology to ensure all content meets our community standards and is appropriate for our users.
                    </p>
                    
                    <p style="color: #666; font-size: 14px; line-height: 1.6;">
                        If you believe this decision is in error, please contact our administrators for manual review.
                    </p>
                    
                    <div class="footer">
                        <p>Thank you for using our service.</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "❌ Video Request - Not Approved"
            msg["From"] = self.sender_email
            msg["To"] = recipient
            
            msg.attach(MIMEText(html_content, "html"))
            
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, recipient, msg.as_string())
            
            logger.info(f"✓ Rejection email sent to {recipient}")
            
        except Exception as e:
            logger.error(f"❌ Error sending email: {str(e)}")
    
    def send_admin_alert_email(self, admin_email: str, youtube_url: str, sender_email: str, reason: str):
        """Send admin alert for manual review"""
        
        logger.info(f"📧 Sending admin alert to {admin_email}")
        
        html_content = f"""
        <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        background-color: #f5f5f5;
                    }}
                    .container {{
                        max-width: 600px;
                        margin: 0 auto;
                        background-color: white;
                        padding: 30px;
                        border-radius: 10px;
                    }}
                    .alert {{
                        background-color: #fff3cd;
                        padding: 15px;
                        border-radius: 5px;
                        border-left: 4px solid #ffc107;
                    }}
                    .details {{
                        background-color: #f9f9f9;
                        padding: 15px;
                        border-radius: 5px;
                        margin: 20px 0;
                    }}
                    .details p {{
                        margin: 10px 0;
                    }}
                    strong {{
                        color: #333;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h2>🚨 Manual Review Required</h2>
                    
                    <div class="alert">
                        <p><strong>A video request requires manual review.</strong></p>
                    </div>
                    
                    <div class="details">
                        <p><strong>From User:</strong> {sender_email}</p>
                        <p><strong>Video URL:</strong> <a href="{youtube_url}">{youtube_url}</a></p>
                        <p><strong>Reason:</strong> {reason}</p>
                        <p><strong>Time:</strong> {json.dumps({"timestamp": "NOW"}).replace('"NOW"', 'from datetime import datetime; datetime.now().isoformat()')}</p>
                    </div>
                    
                    <p>Please review this video request and take appropriate action.</p>
                </div>
            </body>
        </html>
        """
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "🚨 Manual Video Review Needed"
            msg["From"] = self.sender_email
            msg["To"] = admin_email
            
            msg.attach(MIMEText(html_content, "html"))
            
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.sender_email, self.sender_password)
                server.sendmail(self.sender_email, admin_email, msg.as_string())
            
            logger.info(f"✓ Admin alert sent to {admin_email}")
            
        except Exception as e:
            logger.error(f"❌ Error sending admin email: {str(e)}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--type", required=True, choices=["success", "rejection", "admin_alert"])
    parser.add_argument("--recipient", required=True)
    parser.add_argument("--drive-links", default="{}")
    parser.add_argument("--rejection-reason", default="")
    parser.add_argument("--youtube-url", default="")
    parser.add_argument("--sender-email", default="")
    
    args = parser.parse_args()
    
    sender = EmailSender()
    
    if args.type == "success":
        drive_links = json.loads(args.drive_links)
        video_data = {}
        
        # Load video metadata if available
        if os.path.exists("/tmp/videos/info.json"):
            try:
                with open("/tmp/videos/info.json") as f:
                    video_data = json.load(f)
            except:
                pass
        
        sender.send_success_email(args.recipient, video_data, drive_links)
    
    elif args.type == "rejection":
        sender.send_rejection_email(args.recipient, args.rejection_reason)
    
    elif args.type == "admin_alert":
        admin_email = os.getenv("ADMIN_EMAIL")
        sender.send_admin_alert_email(admin_email, args.youtube_url, args.sender_email, args.rejection_reason)

if __name__ == "__main__":
    main()
