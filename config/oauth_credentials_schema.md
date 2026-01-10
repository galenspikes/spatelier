# OAuth Credentials JSON Schema

## 📋 Expected File Structure

The OAuth credentials file should be named:
```
config/youtube_oauth_credentials.json
```

## 🔍 JSON Schema

The file should contain a JSON object with this structure:

```json
{
  "installed": {
    "client_id": "your-client-id.apps.googleusercontent.com",
    "project_id": "your-project-id", 
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "your-client-secret",
    "redirect_uris": [
      "http://localhost"
    ]
  }
}
```

## 🔑 Required Fields

- **`client_id`**: Your OAuth 2.0 Client ID from Google Cloud Console
- **`client_secret`**: Your OAuth 2.0 Client Secret from Google Cloud Console
- **`project_id`**: Your Google Cloud Project ID
- **`auth_uri`**: OAuth authorization endpoint (usually the same)
- **`token_uri`**: OAuth token endpoint (usually the same)
- **`auth_provider_x509_cert_url`**: Certificate URL (usually the same)
- **`redirect_uris`**: Array with "http://localhost" (for local authentication)

## 📁 File Location

Save the file as:
```
config/youtube_oauth_credentials.json
```

## ✅ Validation

The system will check:
1. **File exists** at the correct path
2. **Valid JSON** format
3. **Required fields** are present
4. **Client ID and Secret** are not empty

## 🚨 Common Issues

- **Wrong file name**: Must be exactly `youtube_oauth_credentials.json`
- **Wrong location**: Must be in `config/` directory
- **Invalid JSON**: Check for syntax errors
- **Missing fields**: Ensure all required fields are present
- **Empty values**: Client ID and Secret must have actual values

## 🎯 What You Should See

When you download from Google Cloud Console, you should get a file that looks like:

```json
{
  "installed": {
    "client_id": "123456789-abcdefghijklmnop.apps.googleusercontent.com",
    "project_id": "my-youtube-project-12345",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token", 
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "GOCSPX-abcdefghijklmnopqrstuvwxyz",
    "redirect_uris": [
      "http://localhost"
    ]
  }
}
```

## 🔧 Testing

After saving the file, run:
```bash
spt ssd start "test search"
```

You should see:
- "YouTube API client initialized with OAuth"
- A browser window will open for Google login
- After login, credentials will be saved for future use

