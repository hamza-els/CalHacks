"""Flask web application for extracting events from text and adding to Google Calendar."""
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.utils import secure_filename
import os
from pathlib import Path
import json
from datetime import datetime

from parsers import extract_events_from_text
from calendar_utils import create_google_service, create_google_event

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
    try:
        service = create_google_service()
        # If we get here, OAuth succeeded and token is saved
        session['authenticated'] = True
        return redirect(url_for('index'))
    except Exception as e:
        return f'Error authenticating: {str(e)}', 500


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
        
        for event in events:
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

