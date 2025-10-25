# User Authentication Updates

## What Changed

### 1. Sign-In Button Always Visible
- The "Sign in with Google" button now appears in the header at all times
- You can switch users or sign in at any point

### 2. User Display
- When signed in, you'll see:
  - Your Google profile picture
  - Your email address: "✅ Signed in as your.email@gmail.com"
  - A "Sign Out" button

### 3. Sign-Out Functionality
- Click "Sign Out" to clear your session
- Your token will be deleted
- You'll need to sign in again to create events

### 4. Wrong User Issue Fixed
- To switch users, click "Sign Out" then sign in with the correct account
- The app now clearly shows which user is currently signed in

## How to Use

### First Time / Switching Users

1. **Click "Sign in with Google"** (always visible in header)
2. Select the correct Google account
3. Grant permissions
4. You'll see your email and picture displayed
5. Now you can create events

### Create Events

1. Upload your syllabus
2. Parse events
3. Click "Add to Google Calendar"
4. Events will be created in the calendar of the signed-in user

### Sign Out

1. Click "Sign Out" in the header
2. Token is deleted
3. Sign in again to continue

## Important Notes

- **The sign-in button always appears** so you can switch users anytime
- **Your email is displayed** to confirm which account you're using
- **Sign out and sign in again** if you need to switch users
- The "Add to Google Calendar" button only enables when properly authenticated

## Troubleshooting

**Don't see my email/picture?**
- You need to sign out and sign in again to get user info
- Delete `token.json` and restart Flask

**Want to switch users?**
- Click "Sign Out" in the header
- Click "Sign in with Google" 
- Select a different account

**Events going to wrong calendar?**
- Make sure you're signed in with the correct Google account
- Check the email displayed in the header
- Sign out and sign in with the correct account

