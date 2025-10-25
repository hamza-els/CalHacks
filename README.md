Quick decisions to make up front

Who owns the calendar?

If the end user should get events in their Google Calendar, use OAuth 2.0 user consent flow (recommended for demos). (Google Calendar API). 
Google for Developers
+1

Parsing strategy: rule-based + temporal parser for high precision, or LLM-based extraction for flexibility. I recommend combining both: a deterministic date parser (chrono-node or Python dateparser/Duckling) plus an LLM (OpenAI) for extracting event semantics and fallbacks. (OpenAI function-calling and chrono-node docs). 
OpenAI Platform
+1

Architecture (high level)

Frontend: React (Create React App or Next.js) — file upload UI, preview extracted events, “Create on Google Calendar” button.

Backend: Node.js + Express (or Next.js API routes) — receive file, extract text, parse events, transform into Google Calendar event objects, call Google Calendar API.

NLP/date parsing: combination of OpenAI function-calling (structured extraction) and chrono-node (or Duckling/dateparser) for robust date/time parsing.

Auth: Google OAuth2 for user calendar access (or service account if writing to a specific demo calendar you control).

Storage: temporary memory or small DB (SQLite) to store parsed events for preview (optional).

Deploy: Vercel / Render / Heroku for quick demo.

Tech stack (recommended — easiest path)

Primary (recommended):

Backend: Node.js (16+) + Express (or Next.js API routes)

Frontend: React or Next.js

Google API client: googleapis (Node) — handles OAuth and calendar calls. 
Google for Developers

Date parser: chrono-node (npm) for natural-language dates. 
npm

Optional LLM: OpenAI API with function-calling / structured outputs to extract event fields reliably. 
OpenAI Platform

PDF text extraction: pdf-parse or pdfjs (if users upload PDFs)

File upload middleware: multer (Node)

Timezone/formatting: luxon or date-fns-tz

Alternate (Python)

Backend: FastAPI or Flask

Google client: google-api-python-client

Date parsing: dateparser, quickadd or Duckling (via wrapper) for robust parsing. 
GitHub
+1 

LLM: OpenAI Python SDK (function-calling / structured outputs)

Step-by-step implementation (Node.js + React demo)
0) Prep & accounts

Create Google Cloud project → enable Google Calendar API. 
Google for Developers

Create OAuth 2.0 credentials (Web application). Add redirect URI for your app (e.g., http://localhost:3000/oauth2callback). Download client_secret.json. 
Google for Developers

(If you’ll use OpenAI) Create OpenAI API key. Read function-calling docs to output structured JSON. 
OpenAI Platform

1) Scaffold the repo

npx create-next-app syllabus2calendar (or CRA + Express)

Add backend API route POST /api/parse and POST /api/create-events

Install libs:

npm i googleapis chrono-node multer pdf-parse luxon axios openai

2) Frontend: file upload & preview

Build a simple page:

File input (accept .txt, .pdf, .docx optional)

“Parse” button → sends file to /api/parse

Show parsed events in a table with checkboxes and editable fields (title, date/time, duration, location, description)

“Sign in with Google” / “Create events” button

UI libs: plain React + Tailwind for quick styling.

3) Backend: receive file and extract text

Use multer to accept uploads.

If PDF: use pdf-parse to get text.

If text: read as UTF-8.

Example (rough):

// /api/parse
const text = await extractTextFromUpload(file);

4) NLP → structured events

Approach A (fast, deterministic):

Split doc into lines/sections based on headings (e.g., "Week 1", "Exam", dates).

For each candidate sentence/line, run chrono-node.parse() to find dates/times. If a date is found, treat the surrounding text as an event title/description. 
npm

Normalize start/end using luxon and default duration (e.g., 1 hour for lectures) unless specified.

Approach B (LLM-assisted, higher recall):

Send the full text or chunks to OpenAI with a JSON schema/function asking: extract events with fields:

title, start (ISO), end (ISO or duration), all_day (bool), recurrence (iCal RRULE or human), location, notes.

Use OpenAI function-calling or structured outputs to get consistent JSON. Then run chrono-node on any remaining fuzzy date strings the model returns (to improve deterministic parsing). 
OpenAI Platform
+1

Sample OpenAI function schema (conceptual):

{
  "name": "extract_events",
  "description": "Extract events from syllabus",
  "parameters": {
    "type":"object",
    "properties":{
      "events":{
        "type":"array",
        "items":{
          "type":"object",
          "properties":{
            "title":{"type":"string"},
            "start_text":{"type":"string"},
            "end_text":{"type":"string"},
            "all_day":{"type":"boolean"},
            "location":{"type":"string"},
            "notes":{"type":"string"}
          },
          "required":["title","start_text"]
        }
      }
    }
  }
}


After the LLM returns start_text/end_text, parse them with chrono-node into exact ISO datetimes.

(See OpenAI function-calling docs). 
OpenAI Platform

5) Normalize & validate events

Run each candidate start_text / end_text through chrono-node (or Python dateparser) to get start and end datetimes. If only duration provided, compute end = start + duration.

Validate: start < end; timezone present — if not, attach user’s timezone.

Allow user edit on frontend before upload to calendar.

6) Google Calendar insertion

Implement OAuth 2.0: redirect user to Google consent, get tokens, store in session. googleapis has sample quickstarts. 
Google for Developers

Use calendar.events.insert() to create events (events.insert) — supply start / end either as dateTime (with tz) or date for all-day. 
Google for Developers

Minimal Node snippet:

const {google} = require('googleapis');
const calendar = google.calendar({version: 'v3', auth: oauth2Client});
await calendar.events.insert({
  calendarId: 'primary',
  resource: {
    summary: title,
    description: notes,
    start: { dateTime: startIso, timeZone: 'America/Los_Angeles' },
    end: { dateTime: endIso, timeZone: 'America/Los_Angeles' },
    location,
  }
});

7) Edge cases & features to add

Recurring events (weekly class): try to detect patterns like “every Monday 10–11am” and set an RRULE recurrence. If detected, build recurrence: ['RRULE:FREQ=WEEKLY;BYDAY=MO;COUNT=12'].

Exams and fixed deadlines: treat as single events or all-day events.

Ambiguous dates: present to user for confirmation if parser confidence low.

Time references like “Week 3”: require mapping from syllabus start date or manual anchor input.

Attachment of syllabus to event (add link to notes).

8) Testing & validation

Use a few real syllabi from different instructors — test variations in date formats (e.g., “9/3”, “Sept. 3”, “Thursday Week 2”).

Add unit tests for the parser: give sample sentences and assert expected extracted ISO datetimes.

Manual tests: preview UI, modify event objects, then create on calendar.

Minimal viable demo timeline (one dev)

Day 1: Setup project, Google API credentials, basic upload and text extraction, simple chrono-node tests.

Day 2: Implement parsing pipeline (rule-based) + frontend preview.

Day 3: Add OAuth + calendar create; end-to-end flow.

Day 4: Improve extraction with OpenAI function-calling (optional), add recurrence heuristics, polish UI.

Example mapping: text → event object (JSON)
{
  "title": "Intro to Algorithms (Lecture)",
  "start": "2025-09-03T10:00:00-07:00",
  "end": "2025-09-03T11:00:00-07:00",
  "all_day": false,
  "recurrence": ["RRULE:FREQ=WEEKLY;BYDAY=WE;COUNT=13"],
  "location": "Room 101",
  "notes": "Read Chapter 1 before class"
}

Helpful libraries & docs (quick references)

Google Calendar API quickstart (Node): step-by-step for OAuth and the API. 
Google for Developers

Google Calendar create events guide (events.insert): explains required fields. 
Google for Developers

chrono-node (JS natural language date parsing). 
npm

OpenAI Function Calling & structured output (for reliably extracting JSON from text). 
OpenAI Platform
+1

Duckling (alternative date/time parser) and wrappers if you want a heavyweight but robust extractor. 
GitHub
+1

Tips, pitfalls & best practices

Timezones matter. Always include timezone in calendar event datetimes. Default to user timezone (ask or detect).

Rate limits & quotas. Google and LLM APIs have quotas — batch event creation carefully.

Parsing ambiguity: Syllabi are inconsistent (e.g., “midterm in October” vs “Week 7”). Use human-in-the-loop preview before creating events.

Privacy: if using OpenAI, remember you are sending potentially private course content — disclose it in demo.

Service account vs user OAuth: service accounts are easier for writing into a calendar you control; to write into users’ calendars, you need OAuth consent.