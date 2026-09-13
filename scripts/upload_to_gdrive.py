#!/usr/bin/env python3
"""Upload processed videos to Google Drive with auto-deletion"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime, timedelta
import tempfile

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Configuration
GDRIVE_EXPIRY_DAYS = 2  # Delete files after 2 days
UPLOADED_FILES_LOG = "/tmp/gdrive_uploads.json"  # Track uploaded files

class GoogleDriveManager:
    def __init__(self):
        """Initialize Google Drive service"""
        creds_json = os.getenv("GOOGLE_DRIVE_CREDENTIALS", "{}")
        creds_dict = json.loads(creds_json)
        
        if not creds_dict:
            logger.error("❌ GOOGLE_DRIVE_CREDENTIALS not set")
            return
        
        creds = Credentials.from_service_account_info(creds_dict)
        self.service = build('drive', 'v3', credentials=creds)
        self.uploads_log = self._load_uploads_log()
    
    def _load_uploads_log(self) -> dict:
        """Load or create uploads tracking file"""
        if os.path.exists(UPLOADED_FILES_LOG):
            try:
                with open(UPLOADED_FILES_LOG, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_uploads_log(self):
        """Save uploads tracking file"""
        os.makedirs(os.path.dirname(UPLOADED_FILES_LOG), exist_ok=True)
        with open(UPLOADED_FILES_LOG, 'w') as f:
            json.dump(self.uploads_log, f, indent=2)
    
    def _cleanup_expired_files(self):
        """Delete files older than GDRIVE_EXPIRY_DAYS"""
        logger.info(f"🗑️ Checking for files older than {GDRIVE_EXPIRY_DAYS} days...")
        
        now = datetime.utcnow()
        expired_files = []
        
        for file_id, file_info in list(self.uploads_log.items()):
            upload_time = datetime.fromisoformat(file_info['timestamp'])
            age = (now - upload_time).days
            
            if age >= GDRIVE_EXPIRY_DAYS:
                logger.info(f"🗑️ Deleting expired file: {file_info['filename']} ({age} days old)")
                
                try:
                    self.service.files().delete(fileId=file_id).execute()
                    expired_files.append(file_id)
                    logger.info(f"✓ Deleted: {file_id}")
                except Exception as e:
                    logger.error(f"Failed to delete {file_id}: {str(e)}")
        
        # Remove from log
        for file_id in expired_files:
            del self.uploads_log[file_id]
        
        if expired_files:
            self._save_uploads_log()
            logger.info(f"✓ Cleaned up {len(expired_files)} expired files")
    
    def create_folder(self, folder_name: str) -> str:
        """Create a folder in Google Drive"""
        folder_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        folder = self.service.files().create(
            body=folder_metadata,
            fields='id'
        ).execute()
        
        return folder['id']
    
    def upload_file(self, file_path: str, folder_id: str, filename: str = None) -> dict:
        """Upload a file to Google Drive"""
        if not os.path.exists(file_path):
            logger.error(f"❌ File not found: {file_path}")
            return None
        
        if filename is None:
            filename = os.path.basename(file_path)
        
        file_metadata = {
            'name': filename,
            'parents': [folder_id]
        }
        
        media = MediaFileUpload(file_path, resumable=True)
        
        file_obj = self.service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink, name'
        ).execute()
        
        # Track in log
        self.uploads_log[file_obj['id']] = {
            'filename': filename,
            'folder_id': folder_id,
            'timestamp': datetime.utcnow().isoformat(),
            'size': os.path.getsize(file_path)
        }
        self._save_uploads_log()
        
        logger.info(f"✓ Uploaded: {filename}")
        
        return {
            'id': file_obj['id'],
            'link': file_obj['webViewLink'],
            'name': file_obj['name']
        }
    
    def create_shareable_link(self, file_id: str) -> str:
        """Make file publicly accessible and get shareable link"""
        permission = {
            'type': 'anyone',
            'role': 'reader'
        }
        
        self.service.permissions().create(
            fileId=file_id,
            body=permission
        ).execute()
        
        return f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"

def upload_to_gdrive():
    """Main upload function"""
    
    manager = GoogleDriveManager()
    
    # Clean up expired files first
    manager._cleanup_expired_files()
    
    # Find processed files
    output_dir = Path("/tmp/videos/processed")
    
    if not output_dir.exists():
        logger.error("❌ No processed videos found")
        return
    
    # Get video metadata
    video_title = "Video Download"
    if os.path.exists("/tmp/videos/info.json"):
        try:
            with open("/tmp/videos/info.json") as f:
                info = json.load(f)
                video_title = info.get('title', 'Video Download')
        except:
            pass
    
    # Create folder
    folder_name = f"{video_title}_downloads_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    folder_id = manager.create_folder(folder_name)
    logger.info(f"📁 Created folder: {folder_name}")
    
    # Upload files
    drive_links = {}
    
    for file_path in output_dir.glob("*"):
        if file_path.is_file():
            file_result = manager.upload_file(str(file_path), folder_id)
            
            if file_result:
                fmt = file_path.suffix.lstrip('.')
                drive_links[fmt] = file_result
    
    # Write outputs for GitHub Actions
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"folder_id={folder_id}\n")
            f.write(f"drive_links={json.dumps(drive_links)}\n")
    
    logger.info(f"✓ Upload complete")
    return drive_links

if __name__ == "__main__":
    upload_to_gdrive()
