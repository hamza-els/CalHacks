# Quick Start Guide

## 🚀 Getting Started in 3 Steps

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Start the Server

```bash
python app.py
```

### Step 3: Open in Browser

Navigate to: **http://localhost:5000**

## 📝 Quick Test

1. Go to `http://localhost:5000`
2. Upload `examples/sample_syllabus.txt`
3. Click "Parse Events"
4. Click "Sign in with Google" (first time only)
5. Click "Add to Google Calendar"

Done! Check your Google Calendar for the events.

## 🔑 Required: Google Credentials

Before using Google Calendar features, you need OAuth credentials:

1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Create project → Enable Calendar API
3. Create OAuth 2.0 credentials
4. Download as `credentials.json`
5. Place in project root

See `TESTING.md` for detailed instructions.

## 📁 Project Structure

```
CalHacks/
├── app.py                  # Flask web server
├── parsers.py              # Event extraction logic
├── calendar_utils.py       # Google Calendar integration
├── credentials.json        # ⚠️ Add this yourself
├── requirements.txt        # Python dependencies
├── templates/
│   └── index.html         # Web UI
├── examples/
│   └── sample_syllabus.txt # Test file
└── TESTING.md             # Detailed testing guide
```

## 🎯 Features

- ✅ Upload text files with event dates
- ✅ Automatic event extraction using NLP
- ✅ Preview events before creating
- ✅ Google Calendar integration
- ✅ Modern, responsive UI
- ✅ Drag-and-drop file upload

## ⚠️ Troubleshooting

**"credentials.json not found"**
→ Download OAuth credentials from Google Cloud Console

**"No events found"**
→ Ensure your text file contains date/time information

**OAuth issues**
→ Delete `token.json` and try again

## 📚 Next Steps

- Read `TESTING.md` for comprehensive testing guide
- Check `README.md` for architecture details
- Modify `parsers.py` to improve event extraction
- Add PDF support for better syllabus parsing

## 🎉 Ready to Test!

Run `python app.py` and visit `http://localhost:5000`

