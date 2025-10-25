# Testing Instructions for Syllabus to Calendar Web App

## Prerequisites

Before testing, ensure you have:

1. **Python 3.8+** installed
2. **Google Cloud Credentials** (`credentials.json`) in the project root
3. All dependencies installed

## Installation Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Verify Credentials

Ensure `credentials.json` exists in the project root:
```bash
ls credentials.json
```

If you don't have credentials yet:
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Calendar API
4. Create OAuth 2.0 credentials (Web application)
5. Download credentials as `credentials.json`
6. Place in project root

## Running the Application

### Start the Flask Server

```bash
python app.py
```

You should see output like:
```
 * Running on http://0.0.0.0:5000
 * Debug mode: on
```

### Access the Web Interface

Open your browser and navigate to:
```
http://localhost:5000
```

## Testing Steps

### Test 1: Basic File Upload and Parsing

1. **Open the application** in your browser at `http://localhost:5000`
2. **Upload a file** using the sample syllabus:
   - Click "Choose File"
   - Select `examples/sample_syllabus.txt`
   - OR drag and drop the file into the upload area
3. **Click "Parse Events"**
4. **Verify results**:
   - You should see a success message
   - A table should appear showing extracted events
   - Events should include lectures, labs, exams, and project due dates

**Expected Output:**
- At least 8 events should be extracted
- Events should have proper titles
- Start and end times should be displayed

### Test 2: Google Calendar Integration

1. **Before creating events**, click "Sign in with Google"
2. **Google OAuth popup**:
   - A browser window will open for Google sign-in
   - Select your Google account
   - Grant calendar permissions
   - You'll be redirected back to the app
3. **Return to the main page** and upload the sample syllabus again
4. **Parse events** again
5. **Click "Add to Google Calendar"**
6. **Verify events were created**:
   - You should see a success message
   - Links to created events should appear
   - Check your Google Calendar to confirm events exist

**Expected Output:**
- All events should be created in your Google Calendar
- Events should have correct dates and times
- Clicking the links should open the events in Google Calendar

### Test 3: Custom Text Input

Create a custom test file `test_custom.txt`:

```
Team meeting on December 10, 2025 at 2:00pm
Company party on December 20, 2025 at 6:00pm
Project deadline: December 31, 2025 at 11:59pm
```

Test it the same way as Test 1.

### Test 4: Edge Cases

Test with files containing:
- **No dates**: Should return an error or empty result
- **Ambiguous dates**: Like "next Tuesday" (should parse relative to current date)
- **Multiple dates in same sentence**: Should extract multiple events

## Troubleshooting

### Issue: "credentials.json not found"

**Solution:**
- Download OAuth credentials from Google Cloud Console
- Save as `credentials.json` in project root
- Ensure file is not in `.gitignore` accidentally

### Issue: "Error authenticating"

**Solution:**
- Delete `token.json` and try again
- Check that OAuth consent screen is configured in Google Cloud Console
- Ensure redirect URI includes `http://localhost:5000`

### Issue: "No events found"

**Solution:**
- Check that your text file contains date/time information
- Try the sample syllabus file first
- Ensure file is saved as `.txt` not `.docx`

### Issue: OAuth popup doesn't open

**Solution:**
- Check browser popup blocker settings
- Try a different browser
- Ensure port 5000 is not blocked by firewall

### Issue: Import errors

**Solution:**
```bash
pip install --upgrade -r requirements.txt
```

## Expected Behavior

### First Time Setup
1. Upload file → Parse → Shows events in table
2. Click "Sign in with Google" → Browser popup opens
3. Sign in → Consent screen → Return to app
4. Token saved to `token.json`
5. Upload again → Parse → Create events
6. Events appear in Google Calendar

### Subsequent Uses
1. Upload file → Parse → Shows events
2. Click "Add to Google Calendar" (no sign-in needed)
3. Events created instantly

## Verification Checklist

- [ ] Flask server starts without errors
- [ ] Web interface loads at localhost:5000
- [ ] File upload works (drag-drop and file picker)
- [ ] Events are parsed correctly from sample syllabus
- [ ] Google OAuth flow completes successfully
- [ ] Events are created in Google Calendar
- [ ] Event links work and open calendar items
- [ ] No console errors in browser
- [ ] Token is saved and reused on subsequent runs

## Testing Different Scenarios

### Scenario 1: Class Schedule
```
CS 101 meets every Monday and Wednesday at 10:00am.
Midterm is on October 15, 2025 at 3:00pm.
```

### Scenario 2: Meeting Notes
```
Team standup every Tuesday at 9:00am.
Sprint review on Friday, November 1, 2025 at 2:00pm.
```

### Scenario 3: Personal Events
```
Doctor appointment on December 5, 2025 at 3:00pm.
Birthday party on December 25, 2025 at 7:00pm.
```

## Notes

- The app uses Flask's development server (not production-ready)
- For production, use a proper WSGI server like Gunicorn
- The current implementation supports `.txt` files only
- PDF support requires additional dependencies (`pdf-parse`)
- All uploaded files are stored in `uploads/` directory
- Check browser console (F12) for any JavaScript errors

## Success Criteria

The app is working correctly if:
✅ Files can be uploaded without errors
✅ Events are extracted with correct dates and times
✅ Google OAuth flow completes successfully
✅ Events appear in your Google Calendar
✅ No errors in console or terminal

## Next Steps After Testing

Once basic functionality is verified:
1. Add PDF support for better syllabus parsing
2. Implement timezone detection
3. Add recurring event support
4. Improve date parsing with LLM assistance
5. Add event editing before calendar creation
6. Deploy to production (Heroku, Render, etc.)

