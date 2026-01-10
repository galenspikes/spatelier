# YouTube OAuth Setup Guide

## 🔐 Setting Up OAuth for Personal YouTube Results

### 1. Download OAuth Credentials
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Go to **APIs & Services** → **Credentials**
4. Find your OAuth 2.0 Client ID
5. Click **Download JSON**
6. Save it as `config/youtube_oauth_credentials.json`

### 2. File Structure
```
config/
├── youtube_oauth_credentials.json  # Your OAuth credentials file
└── oauth_setup.md                  # This guide
```

### 3. OAuth Scopes
The system requests these permissions:
- `https://www.googleapis.com/auth/youtube.readonly` - Read YouTube data

### 4. Benefits of OAuth
- **Personal recommendations** - Based on your actual YouTube history
- **Higher rate limits** - 10,000 requests per day (vs 100 for API key)
- **Access to your data** - Watch history, subscriptions, playlists
- **Better search results** - Personalized to your interests

### 5. First Time Setup
When you first run video download with OAuth:
1. A browser window will open
2. Sign in with your Google account
3. Grant permissions to the app
4. The system will save your credentials for future use

### 6. Security
- Credentials are stored locally in `config/youtube_token.pickle`
- Only you have access to your YouTube data
- No data is sent to external servers

### 7. Usage
```bash
# The system will automatically use OAuth if credentials file exists
spt video download "your video url"
```

## Personal Results
With OAuth, you'll get:
- **Personalized recommendations** based on your watch history
- **Better search results** tailored to your interests
- **Access to your subscriptions** and playlists
- **More accurate related videos** based on your preferences
