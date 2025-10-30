"""Flask web application for extracting events from text and adding to Google Calendar."""
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.utils import secure_filename
import os
from pathlib import Path
import json
from datetime import datetime
from dotenv import load_dotenv

from parsers import extract_events_from_text, extract_events_with_gemini
from calendar_utils import create_google_service, create_google_event, create_calendar
from image_processor import extract_events_from_image, get_supported_image_formats

# Load environment variables from .env file
load_dotenv()

# Allow HTTP for localhost OAuth (development only!)
# In production (Render with HTTPS), this should not be set
if os.environ.get('FLASK_ENV') == 'development':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__, static_folder='assets')
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """Render the main upload page."""
    return render_template('index.html')


@app.route('/auth-status')
def auth_status():
    """Check authentication status and return user info."""
    has_token = os.path.exists('token.json')
    user_info = None
    is_authenticated = False
    
    print(f"Auth status check: has_token={has_token}, session_auth={session.get('authenticated')}")
    
    if has_token:
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            
            creds = Credentials.from_authorized_user_file('token.json', 
                [
                    "openid",
                    "https://www.googleapis.com/auth/calendar.events",
                    "https://www.googleapis.com/auth/userinfo.email",
                    "https://www.googleapis.com/auth/userinfo.profile"
                ])
            
            # If credentials are valid (has a token), consider authenticated
            # Check if token exists and hasn't expired
            is_authenticated = creds.valid
            
            if not is_authenticated and creds.token:
                # Token exists, check if expired
                if creds.expired and creds.refresh_token:
                    # Try to refresh
                    try:
                        from google.auth.transport.requests import Request
                        creds.refresh(Request())
                        is_authenticated = True
                    except Exception as e:
                        # If refresh fails due to network issues, still consider authenticated
                        # The token will be refreshed on next API call
                        error_str = str(e)
                        if 'Failed to resolve' in error_str or 'network' in error_str.lower():
                            print(f"Network issue refreshing token, but will treat as authenticated: {e}")
                            is_authenticated = True
                        else:
                            print(f"Could not refresh token: {e}")
                            is_authenticated = False
                else:
                    is_authenticated = not creds.expired
            
            print(f"Auth check: valid={creds.valid}, expired={creds.expired}, has_token={bool(creds.token)}, is_authenticated={is_authenticated}")
            
            if is_authenticated:
                # Try to get user info from Google API
                try:
                    service = build('oauth2', 'v2', credentials=creds)
                    user_info = service.userinfo().get().execute()
                except Exception as e:
                    print(f"Could not fetch user info (will still show as authenticated): {e}")
                    # Authentication is still valid even if we can't get user info
                    pass
        except Exception as e:
            print(f"Error loading credentials: {e}")
    
    return jsonify({
        'authenticated': is_authenticated,
        'has_token': has_token,
        'user': user_info
    })


@app.route('/signout')
def signout():
    """Sign out the user."""
    session['authenticated'] = False
    # Optionally delete token.json to force re-authentication
    if os.path.exists('token.json'):
        os.remove('token.json')
    return redirect(url_for('index'))


@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and parse events for syllabus parsing."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    # Clear any previously stored content when uploading to the syllabus page
    session.pop('events', None)
    session.pop('filename', None)
    
    # Add a unique upload ID for tracking
    import uuid
    upload_id = str(uuid.uuid4())[:8]
    session['upload_id'] = upload_id
    print(f"DEBUG [UPLOAD]: Created upload ID: {upload_id}")
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed. Please upload .txt, .pdf, or image files.'}), 400
    
    # Save file
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    print(f"File saved: {filename}")
    
    # Check if it's an image file
    image_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp'}
    file_ext = '.' + filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    print(f"File extension: {file_ext}")
    
    # Extract events
    try:
        use_gemini = os.environ.get('GEMINI_API_KEY') is not None
        
        if file_ext in image_extensions:
            # Handle image files with Gemini Vision
            print(f"Processing image file: {filename}")
            if not use_gemini:
                return jsonify({'error': 'GEMINI_API_KEY is required for image processing'}), 400
            
            # Process image file using Gemini Vision (extracts events directly)
            events = extract_events_from_image(filepath)
            print(f"Successfully extracted {len(events)} events from image")
            
            # For images, extract text for calendar naming
            # Use event titles as context for calendar name generation
            event_titles = ' '.join([event.get('title', '') for event in events[:5]])  # First 5 event titles
            text = event_titles if event_titles else filename
        else:
            # Read text content from text or PDF files
            try:
                if filename.endswith('.txt'):
                    with open(filepath, 'r', encoding='utf-8') as f:
                        text = f.read()
                elif filename.endswith('.pdf'):
                    # Extract text from PDF using pdfplumber
                    import pdfplumber
                    text = ''
                    with pdfplumber.open(filepath) as pdf:
                        for page in pdf.pages:
                            text += page.extract_text() + '\n'
                else:
                    return jsonify({'error': 'Unsupported file type'}), 400
            except Exception as e:
                return jsonify({'error': f'Error reading file: {str(e)}'}), 500
            
            # Extract events from text
            if use_gemini:
                events = extract_events_with_gemini(text)
            else:
                events = extract_events_from_text(text)
        
        print(f"Serializing {len(events)} events...")
        
        # Convert datetime objects to ISO strings for JSON serialization
        events_serialized = []
        for event in events:
            events_serialized.append({
                'title': event['title'],
                'start': event['start'].isoformat(),
                'end': event['end'].isoformat(),
                'description': event.get('description', ''),
                'location': event.get('location', ''),
                'type': event.get('type', 'event'),
                'all_day': event.get('all_day', False),
                'recurring': event.get('recurring', False)
            })
        
        print(f"Events serialized, storing in session...")
        
        # Store events and filename in session for later use
        # NOTE: We deliberately do NOT store file_content in session because:
        # 1. It causes the session cookie to exceed 4KB (browsers reject it)
        # 2. The file is already saved to disk and can be re-read
        session['events'] = events_serialized
        session['filename'] = filename
        
        print(f"DEBUG [UPLOAD]: Upload ID: {upload_id}")
        print(f"DEBUG: Stored filename: {session.get('filename', '')}")
        
        print("Response ready to send")
        
        return jsonify({
            'success': True,
            'events': events_serialized,
            'count': len(events_serialized)
        })
    except Exception as e:
        return jsonify({'error': f'Error parsing events: {str(e)}'}), 500


@app.route('/oauth')
def oauth():
    """Initiate Google OAuth flow."""
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    
    # OAuth 2.0 settings
    SCOPES = [
        "openid",
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile"
    ]
    
    # Create flow instance
    flow = Flow.from_client_secrets_file(
        'credentials.json',
        scopes=SCOPES,
        redirect_uri=url_for('oauth_callback', _external=True)
    )
    
    # Get authorization URL - use 'consent' to force refresh token
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'  # Force consent screen to get refresh token
    )
    
    # Store state in session
    session['oauth_state'] = state
    
    return redirect(authorization_url)


@app.route('/oauth/callback')
def oauth_callback():
    """Handle OAuth callback."""
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    
    SCOPES = [
        "openid",
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile"
    ]
    
    # Recreate flow
    flow = Flow.from_client_secrets_file(
        'credentials.json',
        scopes=SCOPES,
        redirect_uri=url_for('oauth_callback', _external=True)
    )
    
    # Fetch token
    authorization_response = request.url
    
    # Suppress warnings about scope changes (Google adds 'openid' automatically)
    import warnings
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            flow.fetch_token(authorization_response=authorization_response)
    except Exception as e:
        error_msg = str(e)
        if 'Failed to resolve' in error_msg or 'ConnectionError' in str(type(e).__name__):
            return f"""
            <html>
            <body style="font-family: Arial; padding: 50px; text-align: center;">
                <h1>Network Error</h1>
                <p>Could not connect to Google's servers.</p>
                <p>Error: {error_msg}</p>
                <p><a href="/">Try Again</a></p>
                <p style="margin-top: 30px; color: #666;">
                    This might be a temporary network issue.<br>
                    Please check your internet connection and try again.
                </p>
            </body>
            </html>
            """, 500
        else:
            raise
    
    # Get credentials
    credentials = flow.credentials
    
    # Ensure we have a refresh token
    if not credentials.refresh_token:
        # Try to reload existing token to get refresh token if it exists
        if os.path.exists('token.json'):
            try:
                from google.oauth2.credentials import Credentials
                existing_creds = Credentials.from_authorized_user_file('token.json', SCOPES)
                if existing_creds.refresh_token:
                    credentials.refresh_token = existing_creds.refresh_token
            except Exception:
                pass  # Old token format or invalid, continue without refresh token
    
    # Save credentials
    creds_dict = {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': credentials.scopes
    }
    
    # Add expiry if it exists
    if hasattr(credentials, 'expiry') and credentials.expiry:
        creds_dict['expiry'] = credentials.expiry.isoformat()
    
    with open('token.json', 'w') as token:
        import json
        json.dump(creds_dict, token)
    
    session['authenticated'] = True
    print(f"OAuth callback completed. Session authenticated: {session.get('authenticated')}")
    return redirect(url_for('index'))


@app.route('/create-events', methods=['POST'])
def create_events():
    """Create events in Google Calendar."""
    if 'events' not in session:
        return jsonify({'error': 'No events found. Please upload and parse a file first.'}), 400
    
    # Check if authenticated by checking for token.json (more reliable than session)
    has_token = os.path.exists('token.json')
    if not has_token:
        return jsonify({'error': 'Not authenticated. Please sign in with Google first.'}), 401
    
    try:
        # Get timezone from request or use default
        user_timezone = request.json.get('timezone', 'America/Los_Angeles') if request.is_json else 'America/Los_Angeles'
        
        # Get event indices to create (user selections)
        event_indices = request.json.get('event_indices', []) if request.is_json else []
        
        # Get filename from request body (frontend sends it directly to avoid session cookie issues)
        request_filename = request.json.get('filename', '') if request.is_json else ''
        
        # Get the actual stored filename from session (this is the secure filename saved to disk)
        filename = session.get('filename', '')
        
        service = create_google_service()
        events = session['events']
        
        # Debug: Print filenames
        print(f"DEBUG [CREATE-EVENTS]: Request filename: {repr(request_filename)}")
        print(f"DEBUG [CREATE-EVENTS]: Stored filename: {repr(filename)}")
        
        # Re-read the file content from disk to ensure we get the correct file
        # This guarantees we're always using the most recently uploaded file
        file_content = ''
        if filename:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            if os.path.exists(filepath):
                try:
                    if filename.endswith('.txt'):
                        with open(filepath, 'r', encoding='utf-8') as f:
                            file_content = f.read()
                    elif filename.endswith('.pdf'):
                        import pdfplumber
                        with pdfplumber.open(filepath) as pdf:
                            for page in pdf.pages:
                                file_content += page.extract_text() + '\n'
                except Exception as e:
                    print(f"ERROR reading file for calendar naming: {e}")
            else:
                print(f"WARNING: File '{filename}' not found on disk! Filepath: {filepath}")
                print(f"This usually means old session data. We'll use default calendar name.")
        
        print(f"DEBUG [CREATE-EVENTS]: Upload ID: {session.get('upload_id', 'none')}")
        print(f"DEBUG: filename: {filename}")
        print(f"DEBUG: file_content length: {len(file_content)}")
        print(f"DEBUG: file_content preview: {file_content[:200] if file_content else 'None'}...")
        
        # Check if file_content is actually being passed
        if not file_content or file_content.strip() == '':
            print(f"ERROR: file_content is empty! This means Gemini won't be able to generate a proper calendar name.")
            print(f"Filename: {filename}")
            print(f"Filepath: {filepath if filename else 'None'}")
        
        # Create a new calendar (always creates a new one)
        syllabus_calendar_id, calendar_name = create_calendar(service, file_content, filename)
        
        # Get calendar link
        calendar_link = f"https://calendar.google.com/calendar/render?cid={syllabus_calendar_id}"
        
        # Filter events based on user selection
        if event_indices:
            events_to_create = [events[i] for i in event_indices if 0 <= i < len(events)]
            print(f"Creating {len(events_to_create)} selected events out of {len(events)} total")
        else:
            events_to_create = events
            print(f"No selection made, creating all {len(events)} events")
        
        created_events = []
        
        for event_data in events_to_create:
            try:
                # Create a copy of the event to avoid modifying session data
                event = event_data.copy()
                
                # Convert ISO strings back to datetime objects
                start_dt = datetime.fromisoformat(event['start'])
                end_dt = datetime.fromisoformat(event['end'])
                
                # Validate datetime objects
                if not start_dt or not end_dt:
                    print(f"Skipping event '{event['title']}': Invalid datetime values")
                    continue
                
                # Get event type
                event_type = event_data.get('type', 'event')
                is_all_day = event_data.get('all_day', False) or event_type == 'task'
                
                # Check for valid time range (allow start == end for all-day tasks)
                if not is_all_day and start_dt >= end_dt:
                    print(f"Skipping event '{event['title']}': Start time ({start_dt}) is not before end time ({end_dt})")
                    continue
                
                # For all-day tasks, ensure end_dt is at least start_dt (can be equal)
                if is_all_day and end_dt < start_dt:
                    print(f"Adjusting end time for all-day task '{event['title']}' from {end_dt} to {start_dt}")
                    end_dt = start_dt
                
                event['start'] = start_dt
                event['end'] = end_dt
                
                # Preserve all_day flag
                event['all_day'] = event_data.get('all_day', False)

                event['recurring'] = event_data.get('recurring', False)
                
                result = create_google_event(service, event, calendar_id=syllabus_calendar_id, timezone=user_timezone)
                created_events.append({
                    'title': event['title'],
                    'link': result.get('htmlLink')
                })
            except Exception as e:
                print(f"Error creating event '{event_data.get('title', 'Unknown')}': {e}")
                continue
        
        return jsonify({
            'success': True,
            'message': f'Successfully created {len(created_events)} events in "{calendar_name}" calendar.',
            'events': created_events,
            'calendar_name': calendar_name,
            'calendar_link': calendar_link
        })
    except Exception as e:
        import traceback
        print(f"Error creating events: {e}")
        print(traceback.format_exc())
        return jsonify({'error': f'Error creating events: {str(e)}'}), 500


if __name__ == '__main__':
    # For local development only
    # In production, use: gunicorn -w 1 --timeout 300 --worker-class sync -b 0.0.0.0:$PORT app:app
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug, host='0.0.0.0', port=port)

