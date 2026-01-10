# YouTube Data API v3 Setup

This guide explains how to set up YouTube Data API v3 for real video search and recommendations in the video processing system.

## Prerequisites

- Google Cloud Platform account
- YouTube Data API v3 enabled

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Note your project ID

## Step 2: Enable YouTube Data API v3

1. In the Google Cloud Console, go to "APIs & Services" > "Library"
2. Search for "YouTube Data API v3"
3. Click on it and press "Enable"

## Step 3: Create API Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "API Key"
3. Copy the generated API key
4. (Optional) Restrict the API key to YouTube Data API v3 for security

## Step 4: Set Environment Variable

Add the API key to your environment:

### Option A: Export in Terminal
```bash
export YOUTUBE_API_KEY="your_api_key_here"
```

### Option B: Add to Shell Profile
Add to `~/.zshrc` or `~/.bashrc`:
```bash
export YOUTUBE_API_KEY="your_api_key_here"
```

### Option C: Create .env File
Create `.env` file in project root:
```
YOUTUBE_API_KEY=your_api_key_here
```

## Step 5: Test the Integration

Run the video processing system to test:

```bash
spt video download "https://youtube.com/watch?v=example" --verbose
```

You should see:
- "YouTube API client initialized" in logs
- Real video results instead of mock data
- Actual video metadata from YouTube

## API Quotas and Limits

- **Daily Quota**: 10,000 units per day (default)
- **Search Request**: 100 units
- **Video Details Request**: 1 unit per video

### Quota Usage Examples:
- 1 search with 10 videos = 100 + 10 = 110 units
- 100 searches per day = ~10,000 units (daily limit)

## Troubleshooting

### "No YouTube API key found"
- Ensure `YOUTUBE_API_KEY` environment variable is set
- Restart terminal after setting environment variable
- Check API key is valid and not expired

### "YouTube API error: 403 Forbidden"
- API key may be invalid or restricted
- Check API quotas haven't been exceeded
- Verify YouTube Data API v3 is enabled

### "YouTube API error: 400 Bad Request"
- Invalid search parameters
- Check search query format

## Security Best Practices

1. **Restrict API Key**: Limit to YouTube Data API v3 only
2. **IP Restrictions**: Add your IP address to allowed list
3. **Environment Variables**: Never commit API keys to version control
4. **Rotate Keys**: Regularly rotate API keys for security

## Cost Information

- **Free Tier**: 10,000 units per day
- **Paid Tier**: $0.50 per 1,000 additional units
- **Typical Usage**: 100-500 units per video processing session

## Advanced Configuration

### Custom API Settings
You can customize API behavior in `modules/video/youtube_api.py`:

```python
# Rate limiting
self.min_request_interval = 0.1  # 100ms between requests

# Search parameters
search_response = self.youtube.search().list(
    q=query,
    part='id,snippet',
    type='video',
    maxResults=max_results,
    order='relevance',
    videoDefinition='high',
    videoDuration='medium,long'
).execute()
```

### Fallback Behavior
If YouTube API fails, the system automatically falls back to mock data, ensuring the video processing system continues to work even without API access.
