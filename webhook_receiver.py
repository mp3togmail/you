#!/usr/bin/env python3
"""
Email-to-GitHub Webhook Receiver

Receives emails from Gmail and triggers GitHub Actions workflow.
Deployed on Render, Heroku, Railway, or similar platform.

Environment Variables:
- GMAIL_WEBHOOK_SECRET: Secret key for validating webhook requests
- GITHUB_TOKEN: GitHub personal access token
- GITHUB_OWNER: Repository owner (e.g., mp3togmail)
- GITHUB_REPO: Repository name (e.g., you)
- PORT: Server port (default 5000)
"""

import os
import json
import hmac
import hashlib
import logging
from datetime import datetime
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment
WEBHOOK_SECRET = os.getenv("GMAIL_WEBHOOK_SECRET", "your-secret-key-change-this")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_OWNER = os.getenv("GITHUB_OWNER", "mp3togmail")
GITHUB_REPO = os.getenv("GITHUB_REPO", "you")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")

# GitHub API endpoints
GITHUB_API = "https://api.github.com"
WORKFLOW_NAME = "Email Video Processor - Webhook Trigger"


def validate_webhook_signature(payload_body, signature):
    """Validate webhook signature"""
    expected_signature = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(),
        payload_body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)


def parse_email_body(body):
    """Extract YouTube URL and options from email body"""
    lines = body.lower().split('\n')
    
    data = {
        "youtube_url": "",
        "requested_format": "both",
        "kosher_flag": False,
        "is_admin": False
    }
    
    # Find YouTube URL (look for http/https)
    import re
    url_pattern = r'https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[\w-]+'
    
    for line in lines:
        # Check for YouTube URL
        match = re.search(url_pattern, line)
        if match:
            data["youtube_url"] = match.group(0)
        
        # Check for format preference
        if "mp3" in line and "mp4" not in line:
            data["requested_format"] = "mp3"
        elif "mp4" in line and "mp3" not in line:
            data["requested_format"] = "mp4"
        
        # Check for kosher flag (shorthand for admin approval)
        if "x kosher" in line or "kosher approve" in line:
            data["kosher_flag"] = True
    
    return data


def trigger_github_workflow(email_data):
    """Trigger GitHub Actions workflow with email data"""
    
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    
    # Convert email data to JSON for workflow input
    workflow_input = json.dumps(email_data)
    
    payload = {
        "ref": "main",
        "inputs": {
            "email_data": workflow_input
        }
    }
    
    url = f"{GITHUB_API}/repos/{GITHUB_OWNER}/{GITHUB_REPO}/actions/workflows/{WORKFLOW_NAME}/dispatches"
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 204:
            logger.info(f"✓ Workflow triggered successfully")
            return True
        else:
            logger.error(f"❌ Workflow trigger failed: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error triggering workflow: {str(e)}")
        return False


@app.route("/", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "service": "Email to GitHub Webhook Receiver",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }), 200


@app.route("/health", methods=["GET"])
def status():
    """Status endpoint"""
    return jsonify({
        "status": "running",
        "github_configured": bool(GITHUB_TOKEN),
        "webhook_secret_set": WEBHOOK_SECRET != "your-secret-key-change-this",
        "timestamp": datetime.utcnow().isoformat()
    }), 200


@app.route("/webhook/gmail", methods=["POST"])
def receive_email():
    """
    Receive webhook from Gmail and trigger GitHub Actions
    
    Expected POST body:
    {
        "from": "sender@example.com",
        "subject": "Download YouTube Video",
        "body": "https://www.youtube.com/watch?v=...",
        "timestamp": "2026-09-13T10:30:00Z"
    }
    """
    
    # Validate webhook signature
    signature = request.headers.get("X-Webhook-Signature", "")
    
    if not validate_webhook_signature(request.get_data(), signature):
        logger.warning("❌ Invalid webhook signature")
        return jsonify({"error": "Invalid signature"}), 401
    
    try:
        email_data = request.get_json()
        
        # Validate required fields
        if not email_data.get("from") or not email_data.get("body"):
            return jsonify({"error": "Missing required fields"}), 400
        
        logger.info(f"📧 Received email from {email_data.get('from')}")
        
        # Parse email body
        parsed = parse_email_body(email_data.get("body", ""))
        
        if not parsed["youtube_url"]:
            logger.warning("❌ No YouTube URL found in email")
            return jsonify({"error": "No YouTube URL found"}), 400
        
        # Add sender info
        parsed["sender_email"] = email_data.get("from")
        parsed["is_admin"] = email_data.get("from") == ADMIN_EMAIL
        
        logger.info(f"✓ Parsed email:")
        logger.info(f"  From: {parsed['sender_email']}")
        logger.info(f"  URL: {parsed['youtube_url']}")
        logger.info(f"  Format: {parsed['requested_format']}")
        logger.info(f"  Admin: {parsed['is_admin']}")
        
        # Trigger workflow
        if trigger_github_workflow(parsed):
            return jsonify({
                "status": "queued",
                "message": "Video processing started",
                "url": parsed["youtube_url"]
            }), 202
        else:
            return jsonify({"error": "Failed to trigger workflow"}), 500
            
    except Exception as e:
        logger.error(f"❌ Error processing webhook: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/webhook/admin-action", methods=["POST"])
def admin_action():
    """
    Admin endpoints for manual approval/rejection
    
    Expected POST body:
    {
        "action": "approve" | "reject",
        "target_email": "user@example.com",
        "youtube_url": "https://...",
        "reason": "optional reason"
    }
    """
    
    # Verify admin
    signature = request.headers.get("X-Admin-Signature", "")
    if not validate_webhook_signature(request.get_data(), signature):
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        data = request.get_json()
        action = data.get("action", "").lower()
        
        if action not in ["approve", "reject"]:
            return jsonify({"error": "Invalid action"}), 400
        
        admin_data = {
            "sender_email": data.get("target_email"),
            "youtube_url": data.get("youtube_url"),
            "requested_format": data.get("format", "both"),
            "kosher_flag": action == "approve",
            "is_admin": True,
            "admin_action": True,
            "admin_reason": data.get("reason", "")
        }
        
        logger.info(f"🔑 Admin {action}: {admin_data['youtube_url']}")
        
        if trigger_github_workflow(admin_data):
            return jsonify({
                "status": "queued",
                "action": action,
                "message": f"Admin {action} processed"
            }), 202
        else:
            return jsonify({"error": "Failed to trigger workflow"}), 500
            
    except Exception as e:
        logger.error(f"❌ Admin action error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/test", methods=["POST"])
def test_webhook():
    """
    Test endpoint - doesn't require signature
    Useful for debugging without sending actual emails
    """
    
    try:
        data = request.get_json()
        
        logger.info("🧪 Test webhook received")
        logger.info(f"   Data: {json.dumps(data, indent=2)}")
        
        # Don't actually trigger workflow in test mode
        return jsonify({
            "status": "test_success",
            "message": "Test webhook received",
            "data_received": data
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Test error: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.errorhandler(404)
def not_found(e):
    """404 handler"""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def server_error(e):
    """500 handler"""
    logger.error(f"❌ Server error: {str(e)}")
    return jsonify({"error": "Internal server error"}), 500


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    
    # Verify configuration
    if not GITHUB_TOKEN:
        logger.warning("⚠️  GITHUB_TOKEN not set - workflow triggering will fail")
    
    if WEBHOOK_SECRET == "your-secret-key-change-this":
        logger.warning("⚠️  WEBHOOK_SECRET not changed - security risk!")
    
    logger.info(f"🚀 Starting webhook receiver on port {port}")
    logger.info(f"   GitHub: {GITHUB_OWNER}/{GITHUB_REPO}")
    logger.info(f"   Admin Email: {ADMIN_EMAIL}")
    
    app.run(host="0.0.0.0", port=port, debug=False)
