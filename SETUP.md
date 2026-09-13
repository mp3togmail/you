# Kosher YouTube Downloader - Setup Guide

## Overview

This is a complete email-triggered YouTube downloader service with AI-powered content moderation designed for Chasidish yeshiva boys. Users send emails with YouTube links, and the system automatically:

1. ✅ Downloads the video
2. ✅ Runs AI content analysis (frames + audio)
3. ✅ Processes video (blur inappropriate backgrounds, extract MP3/MP4)
4. ✅ Uploads to Google Drive
5. ✅ Sends formatted HTML email with download links
6. ✅ Auto-deletes files after 2 days

## Architecture

```
Gmail Webhook → Flask Server → GitHub Actions Workflow
                                      ↓
                         1. Download Video (2 min)
                         2. AI Moderation (5 min)
                         3. Process Video (4 min)
                         4. Upload to Drive (2 min)
                         5. Send Email (1 min)
                         ↓
                    User receives links
```

**Total Time:** ~12 minutes end-to-end

## Prerequisites

### 1. GitHub Repository
- Create a new private repository: `mp3togmail/you`
- Enable GitHub Actions
- Set up repository secrets (see below)

### 2. Required APIs & Credentials

#### Gmail Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable Gmail API
4. Create a service account with Gmail API access
5. Generate App Password:
   - Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
   - Select "Mail" and "Windows Computer"
   - Use this password for `GMAIL_APP_PASSWORD`

#### Google Drive Setup
1. Enable Google Drive API in Cloud Console
2. Create service account
3. Download service account key as JSON
4. Share a Google Drive folder with the service account email
5. Use JSON content for `GOOGLE_DRIVE_CREDENTIALS`

#### OpenAI API
1. Get API key from [OpenAI Platform](https://platform.openai.com/api-keys)
2. Set `OPENAI_API_KEY` secret

### 3. YouTube API (Optional)
- For enhanced metadata retrieval
- Set `YOUTUBE_API_KEY` secret

## Setup Instructions

### Step 1: Clone & Install Dependencies

```bash
git clone https://github.com/mp3togmail/you.git
cd you
pip install -r requirements.txt
```

### Step 2: Configure GitHub Secrets

Add these secrets to your repository (Settings → Secrets → New repository secret):

| Secret Name | Value | Notes |
|-------------|-------|-------|
| `GMAIL_SENDER_EMAIL` | your-email@gmail.com | Email address to send from |
| `GMAIL_APP_PASSWORD` | xxxxxxxxxxxxxxxx | Gmail app password |
| `OPENAI_API_KEY` | sk-... | OpenAI API key |
| `GOOGLE_DRIVE_CREDENTIALS` | {...json...} | Service account JSON |
| `YOUTUBE_API_KEY` | (optional) | YouTube API key |
| `ADMIN_EMAIL` | admin@example.com | Admin email for alerts |
| `GITHUB_TOKEN` | ghp_... | GitHub token for workflow dispatch |

### Step 3: Set Up Webhook Receiver

#### Option A: Deploy to Render, Heroku, or Railway

1. Deploy `webhook_receiver.py`:
```bash
gunicorn webhook_receiver:app
```

2. Environment variables needed:
```
GMAIL_WEBHOOK_SECRET=your-secret-key
GITHUB_TOKEN=ghp_xxxxx
PORT=5000
```

#### Option B: Use GitHub Actions only (No external server)

Create a scheduled workflow instead:

```yaml
on:
  schedule:
    - cron: '*/5 * * * *'  # Check every 5 minutes
```

### Step 4: Configure Gmail Webhook

**Note:** Gmail webhooks are limited in Google Apps. Better alternative: Use scheduled workflow or manually trigger via email command.

### Step 5: Test the System

#### Test Email Format:

Send an email to your monitored inbox with:

```
Subject: Download YouTube Video

https://www.youtube.com/watch?v=dQw4w9WgXcQ

Format: both
```

#### Advanced Options in Email:

- **MP3 only:** Include "mp3" in email body
- **MP4 only:** Include "mp4" in email body  
- **Admin bypass:** Admin sends email with "x kosher" to skip checks
- **Admin approval:** Admin sends "approve: [email]" to send to specific user

#### Example Admin Email:

```
approve: user@example.com
https://www.youtube.com/watch?v=dQw4w9WgXcQ
format: mp4
```

## System Components

### 1. Email Receiver (`webhook_receiver.py`)

**Purpose:** Receives webhook notifications from Gmail and triggers GitHub Actions

**Endpoints:**
- `POST /webhook/gmail` - Receives new emails
- `POST /webhook/admin-action` - Admin approval/rejection
- `GET /health` - Health check
- `GET /` - Service info

**Flow:**
1. Validates webhook signature
2. Parses email (extracts URL, format, flags)
3. Triggers GitHub Actions workflow
4. Returns 202 Accepted

### 2. Video Processor (`scripts/fast_video_processor.py`)

**AI Content Analysis:**
- **Video Frames:** Analyzes key frames using GPT-4 Vision
  - Detects adult content
  - Detects inappropriate nudity
  - Detects revealing clothing
  - Identifies regions needing blur
  
- **Audio:** Uses Whisper + Moderation API
  - Transcribes speech
  - Detects explicit content
  - Finds inappropriate segments

**Video Processing:**
- Blurs identified regions
- Removes flagged audio segments
- Extracts MP3 from audio
- Maintains MP4 video quality

### 3. Google Drive Manager (`scripts/upload_to_gdrive.py`)

**Features:**
- Creates organized folders per video
- Uploads MP3 and/or MP4
- Tracks file creation time
- Auto-deletes files after 2 days
- Maintains `/tmp/gdrive_uploads.json` log

**Auto-Deletion Logic:**
```python
if (now - file_upload_time).days >= 2:
    delete_file(file_id)
    remove_from_log()
```

### 4. Email Sender (`scripts/send_email.py`)

**Email Templates:**

#### Success Email
- Video thumbnail
- Title and description
- Download buttons (MP3 and/or MP4)
- Expiration notice (2 days)
- "KOSHER APPROVED" badge

#### Rejection Email
- Rejection reason
- Contact admin link
- Professional formatting

#### Admin Alert
- YouTube URL
- Sender email
- Failure reason
- Timestamp

## Configuration Options

### Video Processing Settings

Edit `scripts/fast_video_processor.py`:

```python
class FastAIModerator:
    def __init__(self):
        self.max_frames = 10  # Number of frames to analyze
        self.client = AsyncOpenAI(...)
```

### Google Drive Expiry

Edit `scripts/upload_to_gdrive.py`:

```python
GDRIVE_EXPIRY_DAYS = 2  # Change to 1, 3, 7, etc.
```

### Email Templates

Edit `scripts/send_email.py` to customize:
- Colors and branding
- Footer messages
- Warning text
- Button styling

## Monitoring & Logs

### View GitHub Actions Logs

```bash
gh run list --repo mp3togmail/you
gh run view {RUN_ID} --repo mp3togmail/you --log
```

### Check Google Drive Auto-Deletion Log

```bash
cat /tmp/gdrive_uploads.json
```

### Email Sending Issues

Check:
1. `GMAIL_APP_PASSWORD` is correct (not regular Gmail password)
2. "Less secure app access" is enabled (if not using app password)
3. Gmail account isn't rate-limited
4. Recipient email is valid

## Troubleshooting

### Issue: "Invalid YouTube URL"
**Solution:** Ensure URL is in format:
- `https://www.youtube.com/watch?v=VIDEO_ID`
- `https://youtu.be/VIDEO_ID`

### Issue: AI Moderation fails
**Solution:** 
- Check `OPENAI_API_KEY` is valid
- Verify you have OpenAI credits
- Check API rate limits

### Issue: Google Drive upload fails
**Solution:**
- Verify service account has Drive access
- Check JSON credentials are valid
- Ensure shared folder exists
- Verify file isn't too large

### Issue: Email not sending
**Solution:**
- Verify Gmail app password (not regular password)
- Check `GMAIL_SENDER_EMAIL` and `GMAIL_APP_PASSWORD`
- Ensure Gmail isn't blocking access

### Issue: Workflow takes too long
**Solution:**
- Reduce `max_frames` in AI moderator (currently 10)
- Use smaller video resolution
- Increase GitHub Actions timeout (currently 15 min)

## Advanced Features

### Admin Panel (Future)

Create web interface for:
- Manual video approval
- View upload history
- Manage user whitelist
- Configure moderation settings

### Statistics Dashboard (Future)

Track:
- Total videos processed
- Approval rate
- Average processing time
- Storage usage
- Common rejection reasons

### Email Command Parser (Future)

Support commands in email:
- `!approve [email] [URL]` - Admin approve for user
- `!reject [email] [URL]` - Admin reject
- `!stats` - Get statistics
- `!help` - Show commands

## Security Considerations

### 1. Data Privacy
- All files deleted after 2 days
- No video metadata stored permanently
- Transcripts not logged

### 2. Access Control
- Admin commands require admin email
- Webhook signature validation
- GitHub secret encryption
- Service account with minimal permissions

### 3. Rate Limiting (TODO)
- Implement user quotas
- Prevent email bombing
- Queue large requests

### 4. Content Moderation
- AI-based automatic detection
- Admin manual review for edge cases
- Community standards enforcement

## Cost Estimation

### Monthly Costs (Approximate)

| Service | Usage | Cost |
|---------|-------|------|
| OpenAI (Vision + Whisper + Moderation) | ~50 videos/month | $10-20 |
| Google Drive | 1TB (shared) | $10 |
| GitHub Actions | 15 min × 50 = 750 min | Free (2000 min/month) |
| Gmail API | Unlimited | Free |
| Hosting (webhook receiver) | 24/7 uptime | $5-10 |
| **Total** | | **$25-40/month** |

## Maintenance

### Weekly Tasks
- [ ] Check GitHub Actions for failures
- [ ] Review admin alert emails
- [ ] Monitor OpenAI usage/costs

### Monthly Tasks
- [ ] Clean up old logs
- [ ] Review rejection statistics
- [ ] Update AI moderation rules if needed
- [ ] Backup configuration

### Quarterly Tasks
- [ ] Review and update security practices
- [ ] Audit user list
- [ ] Update dependencies

## Support & Contact

For issues:
1. Check troubleshooting section above
2. Review GitHub Actions logs
3. Contact project administrator

## License

This project is designed for community use. Please respect all local and national laws regarding video downloading and content moderation.

---

**Last Updated:** September 13, 2026
**Version:** 1.0.0
**Status:** Beta
