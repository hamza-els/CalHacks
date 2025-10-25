# 📅 Syllabus to Calendar Converter

A web application that extracts events and tasks from academic syllabi and automatically creates them in Google Calendar using AI-powered parsing.

## Features

- 🤖 **AI-Powered Parsing**: Uses Google Gemini AI to intelligently extract events from syllabi
- 📝 **Smart Categorization**: Distinguishes between events (lectures, labs, exams) and tasks (assignments, projects)
- 🌍 **Timezone Support**: Automatically detects and uses your local timezone
- 📅 **Google Calendar Integration**: Direct integration with Google Calendar
- 🎨 **Modern UI**: Clean, responsive web interface

## Quick Start

### Prerequisites

- Python 3.8+
- Google account
- Gemini API key (free tier available)

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Setup Google Cloud Project

#### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Enter project name (e.g., "Syllabus Calendar") and click "Create"

#### Step 2: Enable APIs

1. In your project, go to "APIs & Services" → "Library"
2. Search for and enable:
   - **Google Calendar API**
   - **Google OAuth2 API**

#### Step 3: Create OAuth Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Select "Web application"
4. **Add Authorized redirect URI**: `http://localhost:5000/oauth/callback`
5. Click "Create"
6. Download credentials as `credentials.json`
7. Place `credentials.json` in the project root

#### Step 4: Configure OAuth Consent Screen

1. Go to "APIs & Services" → "OAuth consent screen"
2. Select "External" → "Create"
3. Fill in required fields:
   - App name: Syllabus Calendar
   - User support email: your email
   - Developer contact: your email
4. Click "Save and Continue"
5. In "Scopes", click "Add or Remove Scopes"
6. Add scopes:
   - `.../auth/calendar.events`
   - `.../auth/userinfo.email`
   - `.../auth/userinfo.profile`
7. Save and continue
8. Add test users (your email) if needed
9. Back to "Credentials", click "Edit" on your OAuth client
10. Under "Authorized redirect URIs", add: `http://localhost:5000/oauth/callback`
11. Save

### 3. Setup Gemini API (Optional)

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Click "Create API Key"
3. Copy the API key

### 4. Create .env File

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your-gemini-api-key-here
SECRET_KEY=dev-secret-key-change-in-production
```

> **Note**: Gemini API is optional - the app falls back to basic date parsing if not provided.

### 5. Run the Application

```bash
python app.py
```

Open your browser and navigate to: **http://localhost:5000**

## Usage

1. **Sign in with Google**: Click "Sign in with Google" in the header
2. **Upload Syllabus**: Click "Choose File" and select your syllabus (.txt format)
3. **Parse Events**: Click "Parse Events" to extract events and tasks
4. **Review**: Check the extracted events (indicated as 📅 Event or 📝 Task)
5. **Create Calendar**: Click "Add to Google Calendar" to create events

## Project Structure

```
CalHacks/
├── app.py                  # Flask web server
├── parsers.py              # Event extraction logic (Gemini AI + dateparser)
├── calendar_utils.py       # Google Calendar integration
├── credentials.json        # Google OAuth credentials (add this)
├── token.json             # User authentication token (auto-generated)
├── .env                   # Environment variables (create this)
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html         # Web UI
└── examples/
    └── sample_syllabus.txt # Sample test file
```

## Features Explained

### Event vs Task

- **Events**: Lectures, labs, discussions, exams, meetings
  - Have specific start and end times
  - Show location if mentioned
  
- **Tasks**: Assignments, projects, homework
  - Only have due dates (all-day events)
  - No time component

### Timezone Handling

The app automatically detects your browser's timezone and uses it for all calendar events. No manual configuration needed!

## Troubleshooting

### "redirect_uri_mismatch" Error

- Make sure `http://localhost:5000/oauth/callback` is added to Authorized redirect URIs in Google Cloud Console

### "access_denied" Error

- Add your email as a test user in OAuth consent screen
- Make sure OAuth consent screen is published or in testing mode

### Events Times Are Wrong

- The app now uses your local timezone automatically
- If issues persist, check your browser's timezone settings

### Gemini API Not Working

- The app automatically falls back to dateparser if Gemini API key is not set
- Gemini API is completely optional for basic functionality

## Requirements

- Python 3.8+
- Google Cloud account
- Google account for calendar access
- Gemini API key (optional, free tier available)

## Technologies Used

- **Backend**: Flask (Python)
- **AI Parsing**: Google Gemini AI
- **Calendar**: Google Calendar API
- **Date Parsing**: dateparser
- **Frontend**: HTML/CSS/JavaScript

## License

See LICENSE file for details.
