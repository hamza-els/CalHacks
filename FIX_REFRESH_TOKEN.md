# Fix: Missing Refresh Token Error

## Problem
You're seeing: "Authorized user info was not in the expected format, missing fields refresh_token"

## Solution: Re-authenticate

Your current `token.json` doesn't have a refresh token. You need to delete it and sign in again.

### Step 1: Delete the old token

**Windows PowerShell:**
```powershell
del token.json
```

**Windows Command Prompt:**
```cmd
del token.json
```

**Linux/Mac:**
```bash
rm token.json
```

### Step 2: Restart Flask

Stop the Flask server (Ctrl+C) and restart:
```bash
python app.py
```

### Step 3: Sign in again

1. Go to http://localhost:5000
2. Click "Sign in with Google"
3. Complete the OAuth flow
4. You should see a green indicator saying "✅ Signed in with Google"

### Step 4: Test event creation

1. Upload your syllabus
2. Parse events
3. Click "Add to Google Calendar"
4. It should work now!

## Why This Happens

The first time you authenticated, the flow didn't properly save the refresh token. By deleting `token.json` and re-authenticating, the new OAuth flow will properly save the refresh token.

## Visual Indicator

After successful sign-in, you'll see:
- **Green badge** at the top: "✅ Signed in with Google"
- **Orange badge** if not signed in: "⚠️ Not signed in"

The "Add to Google Calendar" button will only be enabled when you're properly authenticated.

## Still Having Issues?

1. **Clear browser cache** and try again
2. **Check credentials.json** exists in project root
3. **Make sure Google Calendar API is enabled** in your Google Cloud project
4. **Verify redirect URI** is set to `http://localhost:5000/oauth/callback`

