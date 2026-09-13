"""
Gmail Webhook Receiver & GitHub Actions Trigger
Receives real-time email notifications and triggers fast video processing
"""

from flask import Flask, request, jsonify
import json
import os
import hmac
import hashlib
from datetime import datetime
import logging
import subprocess
import base64
from typing import Dict, Any

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security
GMAIL_WEBHOOK_SECRET = os.getenv("GMAIL_WEBHOOK_SECRET")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = "mp3togmail"
REPO_NAME = "you"

class EmailProcessor:
    """Fast email processor for webhook events"""
    
    @staticmethod
    def validate_webhook_signature(payload: str, signature: str) -> bool:
        """Validate Gmail webhook signature"""
        expected_sig = hmac.new(
            GMAIL_WEBHOOK_SECRET.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected_sig)
    
    @staticmethod
    def parse_email_data(email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract critical information from email"""
        try:
            # Get email headers
            headers = email_data.get("headers", {})
            from_email = headers.get("from", "unknown")
            subject = headers.get("subject", "")
            
            # Parse body
            body = email_data.get("body", "")
            
            # Extract YouTube URL from email body
            import re
            youtube_pattern = r'(https?://(?:www\.)?youtube\.com/watch\?v=[\w-]+|https?://youtu\.be/[\w-]+)'
            youtube_urls = re.findall(youtube_pattern, body)
            
            if not youtube_urls:
                return {"error": "No YouTube URL found in email"}
            
            youtube_url = youtube_urls[0]
            
            # Check for format requests
            requested_format = "both"
            if "mp3" in body.lower() and "mp4" not in body.lower():
                requested_format = "mp3"
            elif "mp4" in body.lower() and "mp3" not in body.lower():
                requested_format = "mp4"
            
            # Check for admin kosher flag
            kosher_flag = "x kosher" in body.lower()
            
            # Check if admin
            admin_email = os.getenv("ADMIN_EMAIL", "")
            is_admin = from_email == admin_email
            
            return {
                "sender_email": from_email,
                "subject": subject,
                "youtube_url": youtube_url,
                "requested_format": requested_format,
                "kosher_flag": kosher_flag,
                "is_admin": is_admin,
                "timestamp": datetime.utcnow().isoformat(),
                "body": body
            }
        except Exception as e:
            logger.error(f"Error parsing email: {str(e)}")
            return {"error": str(e)}
    
    @staticmethod
    def trigger_github_workflow(email_data: Dict[str, Any]) -> bool:
        """Trigger GitHub Actions workflow instantly"""
        try:
            import requests
            
            workflow_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/email-processor-webhook.yml/dispatches"
            
            headers = {
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            payload = {
                "ref": "main",
                "inputs": {
                    "email_data": json.dumps(email_data)
                }
            }
            
            response = requests.post(workflow_url, json=payload, headers=headers)
            
            if response.status_code == 204:
                logger.info("✓ Workflow triggered successfully")
                return True
            else:
                logger.error(f"Failed to trigger workflow: {response.status_code} {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error triggering workflow: {str(e)}")
            return False


@app.route("/webhook/gmail", methods=["POST"])
def gmail_webhook():
    """
    Receive Gmail webhook notifications
    Triggered instantly when new email arrives
    """
    try:
        # Get webhook data
        webhook_data = request.get_json()
        
        # Validate signature
        signature = request.headers.get("X-Gmail-Signature", "")
        payload = request.get_data(as_text=True)
        
        if not EmailProcessor.validate_webhook_signature(payload, signature):
            logger.warning("Invalid webhook signature")
            return jsonify({"error": "Invalid signature"}), 401
        
        logger.info(f"📧 Email received at {datetime.utcnow().isoformat()}")
        
        # Parse email
        email_data = EmailProcessor.parse_email_data(webhook_data)
        
        if "error" in email_data:
            logger.error(f"Parse error: {email_data['error']}")
            return jsonify(email_data), 400
        
        # Trigger GitHub Actions workflow
        success = EmailProcessor.trigger_github_workflow(email_data)
        
        if success:
            return jsonify({
                "status": "success",
                "message": "Processing started",
                "youtube_url": email_data["youtube_url"],
                "sender": email_data["sender_email"],
                "format": email_data["requested_format"]
            }), 202
        else:
            return jsonify({
                "status": "error",
                "message": "Failed to trigger workflow"
            }), 500
            
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/webhook/admin-action", methods=["POST"])
def admin_webhook():
    """
    Receive admin approval/rejection actions
    Admin sends email with video link + recipient + approval action
    """
    try:
        admin_data = request.get_json()
        
        # Validate it's from admin
        signature = request.headers.get("X-Admin-Signature", "")
        payload = request.get_data(as_text=True)
        
        if not EmailProcessor.validate_webhook_signature(payload, signature):
            return jsonify({"error": "Invalid signature"}), 401
        
        logger.info("👨‍💼 Admin action received")
        
        # Parse admin action
        youtube_url = admin_data.get("youtube_url")
        target_email = admin_data.get("target_email")
        action = admin_data.get("action")  # "approve" or "send"
        
        if not all([youtube_url, target_email, action]):
            return jsonify({"error": "Missing required fields"}), 400
        
        # Create admin action data
        admin_action_data = {
            "sender_email": target_email,
            "youtube_url": youtube_url,
            "requested_format": "both",
            "kosher_flag": True,  # Admin bypasses checks
            "is_admin": True,
            "admin_action": action,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Trigger workflow
        success = EmailProcessor.trigger_github_workflow(admin_action_data)
        
        if success:
            return jsonify({
                "status": "success",
                "message": f"Admin action '{action}' triggered",
                "target_email": target_email
            }), 202
        else:
            return jsonify({"status": "error"}), 500
            
    except Exception as e:
        logger.error(f"Admin webhook error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Gmail Webhook Receiver",
        "timestamp": datetime.utcnow().isoformat()
    }), 200


@app.route("/", methods=["GET"])
def index():
    """Service info"""
    return jsonify({
        "service": "Kosher YouTube Downloader - Gmail Webhook Receiver",
        "version": "1.0.0",
        "endpoints": {
            "webhook": "/webhook/gmail",
            "admin": "/webhook/admin-action",
            "health": "/health"
        }
    }), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    logger.info(f"🚀 Starting webhook receiver on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
