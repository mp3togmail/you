# Kosher YouTube Downloader 📥

> Email-triggered YouTube downloader with AI content moderation for Chasidish yeshiva boys

## Overview

Send an email with a YouTube link → Get approved video in your inbox within ~12 minutes!

### What it does:
1. ✅ Receives emails with YouTube links
2. ✅ Downloads video automatically
3. ✅ Analyzes content with AI (video frames + audio)
4. ✅ Processes video (blurs inappropriate backgrounds, extracts MP3/MP4)
5. ✅ Uploads to Google Drive
6. ✅ Sends formatted HTML email with download links
7. ✅ Auto-deletes files after 2 days for privacy

## Quick Start

### 1. Setup
```bash
# Clone repository
git clone https://github.com/mp3togmail/you.git
cd you

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

### 2. Configure Secrets
Add to GitHub Settings → Secrets:
- `GMAIL_SENDER_EMAIL` - Email to send from
- `GMAIL_APP_PASSWORD` - Gmail app password
- `OPENAI_API_KEY` - OpenAI API key
- `GOOGLE_DRIVE_CREDENTIALS` - Google Drive service account JSON
- `ADMIN_EMAIL` - Admin email address
- `GITHUB_TOKEN` - GitHub token for workflow dispatch

### 3. Deploy Webhook (Optional)
To receive real-time email notifications, deploy the webhook receiver:

```bash
# Deploy to Render, Heroku, Railway, etc.
pip install gunicorn
gunicorn webhook_receiver:app
```

### 4. Test
Send an email to your monitored inbox:
```
Subject: Download Video

https://www.youtube.com/watch?v=dQw4w9WgXcQ
```

That's it! You'll receive the processed video within ~12 minutes.

## Email Formats

### Standard Request
```
Subject: anything

https://www.youtube.com/watch?v=VIDEO_ID
```

### Format Preference
```
Just want MP3:
https://www.youtube.com/watch?v=VIDEO_ID
mp3

Just want MP4:
https://www.youtube.com/watch?v=VIDEO_ID
mp4
```

### Admin Bypass (requires admin email)
```
Subject: x kosher

https://www.youtube.com/watch?v=VIDEO_ID

This bypasses AI moderation checks
```

## System Architecture

```
┌─────────────┐
│   Gmail     │ ← User sends email with YouTube URL
└──────┬──────┘
       │
       ▼
┌─────────────────────────┐
│  Webhook Receiver       │ (Optional: Real-time notifications)
│  (Render/Heroku/etc)    │
└──────────┬──────────────┘
           │
           ▼
┌──────────────────────────────────────┐
│  GitHub Actions Workflow (15 min)    │
├──────────────────────────────────────┤
│ 1. Download Video (2 min)            │
│ 2. AI Moderation (5 min)             │
│    - Vision: frame analysis          │
│    - Audio: Whisper transcription    │
│ 3. Process Video (4 min)             │
│    - Blur inappropriate regions      │
│    - Extract MP3 audio               │
│ 4. Upload to Drive (2 min)           │
│ 5. Send Email (1 min)                │
└──────────┬───────────────────────────┘
           │
           ▼
    ┌─────────────┐
    │  Google     │ ← Files stored for 2 days
    │   Drive     │
    └──────┬──────┘
           │
           ▼
    ┌─────────────────┐
    │  User's Inbox   │ ← Email with download links
    └─────────────────┘
```

## Components

| File | Purpose | Language |
|------|---------|----------|
| `scripts/download_video.py` | YouTube download (yt-dlp) | Python |
| `scripts/run_moderation.py` | AI content analysis (GPT-4V + Whisper) | Python |
| `scripts/process_video.py` | Video/audio processing (FFmpeg) | Python |
| `scripts/upload_to_gdrive.py` | Google Drive upload with auto-deletion | Python |
| `scripts/send_email.py` | Beautiful HTML email templates | Python |
| `webhook_receiver.py` | Real-time email webhook receiver | Python |
| `.github/workflows/email-processor-webhook.yml` | Main orchestration | YAML |

## Features

### 🤖 AI Content Moderation
- **Video Analysis:** Detects inappropriate content using GPT-4 Vision
- **Audio Analysis:** Transcribes and moderates speech using Whisper
- **Auto Blur:** Automatically blurs flagged regions
- **Segment Removal:** Removes flagged audio segments
- **Admin Bypass:** Admins can approve content instantly

### 📧 Beautiful Email Templates
- Video thumbnails
- Download buttons (MP3 & MP4)
- Expiration notice (2 days)
- Professional HTML styling
- Mobile-responsive design

### 🔐 Security
- Webhook signature validation
- Admin-only commands
- No data persistence
- Auto-delete after 2 days
- Service account permissions

### ⚡ Performance
- Total time: ~12 minutes
- Parallel processing where possible
- Efficient video compression
- Optimized AI API calls

## Configuration

### Video Processing
Edit `scripts/process_video.py`:
```python
class FastAIModerator:
    max_frames = 10  # Number of frames to analyze
    blur_intensity = 0.8  # Blur strength (0-1)
```

### Google Drive Expiry
Edit `scripts/upload_to_gdrive.py`:
```python
GDRIVE_EXPIRY_DAYS = 2  # Change as needed (1, 3, 7, etc.)
```

### Email Templates
Edit `scripts/send_email.py` to customize:
- Colors and branding
- Footer messages
- Warning text
- Button styling

## Monitoring

### View Workflow Runs
```bash
gh run list --repo mp3togmail/you
gh run view {RUN_ID} --log
```

### Check Upload Log
```bash
cat /tmp/gdrive_uploads.json
```

### Email Delivery Issues
Check:
1. `GMAIL_APP_PASSWORD` is correct (not regular password)
2. Gmail account isn't rate-limited
3. Recipient email is valid
4. Check GitHub Actions logs for errors

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Invalid YouTube URL" | Use format: `https://youtube.com/watch?v=ID` or `https://youtu.be/ID` |
| AI Moderation fails | Check OpenAI API key and credits |
| Google Drive upload fails | Verify service account JSON and folder sharing |
| Email not sending | Check Gmail app password (not regular password) |
| Workflow too slow | Reduce `max_frames` or increase GitHub Actions timeout |

See [SETUP.md](SETUP.md) for detailed troubleshooting and advanced configuration.

## Cost Estimation

| Service | Cost/month |
|---------|-----------|
| OpenAI (Vision + Whisper) | $10-20 |
| Google Drive | $10 |
| GitHub Actions | Free (2000 min/month) |
| Hosting (webhook) | $5-10 |
| **Total** | **$25-40** |

## Advanced Features (Future)

- [ ] Admin web dashboard
- [ ] Statistics tracking
- [ ] Email command parser
- [ ] User quotas/rate limiting
- [ ] Batch processing
- [ ] Custom moderation rules

## Documentation

- **[SETUP.md](SETUP.md)** - Complete setup and configuration guide
- **[Architecture](SETUP.md#architecture)** - System design overview
- **[Security](SETUP.md#security-considerations)** - Security practices

## Support

For issues or questions:
1. Check [SETUP.md](SETUP.md) troubleshooting section
2. Review GitHub Actions workflow logs
3. Contact project administrator

## License

This project is designed for community use. Please respect all local and national laws regarding video downloading and content moderation.

## Project Status

**Version:** 1.0.0  
**Status:** Beta  
**Last Updated:** September 13, 2026  

---

**Made with ❤️ for the community**
