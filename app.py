"""Flask web application for extracting events from text and adding to Google Calendar."""
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.utils import secure_filename
import os
from pathlib import Path
import json
from datetime import datetime

from parsers import extract_events_from_text
from calendar_utils import create_google_service, create_google_event

# Allow HTTP for localhost OAuth (development only!)
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf'}
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
    """Handle file upload and parse events."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed. Please upload .txt or .pdf files.'}), 400
    
    # Save file
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    # Read text content
    try:
        if filename.endswith('.txt'):
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read()
        elif filename.endswith('.pdf'):
            # For now, just read as text. Install pdf-parse for proper PDF support
            return jsonify({'error': 'PDF support coming soon. Please use .txt files for now.'}), 400
        else:
            return jsonify({'error': 'Unsupported file type'}), 400
    except Exception as e:
        return jsonify({'error': f'Error reading file: {str(e)}'}), 500
    
    # Extract events
    try:
        events = extract_events_from_text(text)
        
        # Convert datetime objects to ISO strings for JSON serialization
        events_serialized = []
        for event in events:
            events_serialized.append({
                'title': event['title'],
                'start': event['start'].isoformat(),
                'end': event['end'].isoformat(),
                'description': event.get('description', ''),
                'location': event.get('location', '')
            })
        
        # Store events in session for later use
        session['events'] = events_serialized
        
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
    
    if not session.get('authenticated'):
        return jsonify({'error': 'Not authenticated. Please sign in with Google first.'}), 401
    
    try:
        service = create_google_service()
        events = session['events']
        created_events = []
        
        for event_data in events:
            # Create a copy of the event to avoid modifying session data
            event = event_data.copy()
            
            # Convert ISO strings back to datetime objects
            event['start'] = datetime.fromisoformat(event['start'])
            event['end'] = datetime.fromisoformat(event['end'])
            
            result = create_google_event(service, event)
            created_events.append({
                'title': event['title'],
                'link': result.get('htmlLink')
            })
        
        return jsonify({
            'success': True,
            'message': f'Successfully created {len(created_events)} events',
            'events': created_events
        })
    except Exception as e:
        return jsonify({'error': f'Error creating events: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

