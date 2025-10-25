# Fix: redirect_uri_mismatch Error

## Problem
You're seeing: "Error 400: redirect_uri_mismatch" when trying to sign in with Google.

## Solution (2 minutes)

### Step 1: Go to Google Cloud Console
1. Visit https://console.cloud.google.com/
2. Select your project

### Step 2: Navigate to Credentials
1. Click "APIs & Services" in the left menu
2. Click "Credentials"

### Step 3: Edit Your OAuth Client
1. Find your OAuth 2.0 Client ID (the one you downloaded as `credentials.json`)
2. Click the edit icon (pencil) next to it

### Step 4: Add Redirect URI
1. Scroll down to "Authorized redirect URIs"
2. Click "+ ADD URI"
3. Enter exactly: `http://localhost:5000/oauth/callback`
4. Click "Save"

### Step 5: Try Again
1. Delete `token.json` from your project folder (if it exists)
2. Restart your Flask app: `python app.py`
3. Try signing in again

## Visual Guide

```
Google Cloud Console
├── Select Project
├── APIs & Services
│   └── Credentials
│       └── [Your OAuth Client]
│           └── Authorized redirect URIs
│               └── Add: http://localhost:5000/oauth/callback
```

## Quick Check

After saving, your OAuth client should have:
- ✅ `http://localhost:5000/oauth/callback` in the list
- ✅ Type: "Web application" (not "Desktop")

## Still Having Issues?

1. **Wait 5 minutes** - Changes can take a few minutes to propagate
2. **Clear browser cache** - Try incognito/private mode
3. **Check credentials.json** - Make sure it's from the correct OAuth client
4. **Verify Flask is running** - Port 5000 should be available

## Why This Happens

Google OAuth requires that your redirect URI matches exactly what's configured in Google Cloud Console. Since we updated the code to use the proper web OAuth flow, we need to configure the matching redirect URI.

