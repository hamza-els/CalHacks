"""Image processing utilities for extracting events from syllabi images using Gemini Vision.

This module uses Google Gemini's vision capabilities to extract text and events
directly from images, which is more accurate than traditional OCR for complex documents.

Requirements:
    - google-generativeai: Google's Gemini API with vision support
    - pillow: Image processing library
"""

from typing import List, Dict, Optional
from PIL import Image
import io
import os
import threading

from parsers import extract_events_from_text


class TimeoutError(Exception):
    pass


def timeout_handler(func, timeout_seconds=60):
    """Execute a function with a timeout using threading."""
    result = [None]
    exception = [None]
    
    def target():
        try:
            result[0] = func()
        except Exception as e:
            exception[0] = e
    
    thread = threading.Thread(target=target)
    thread.daemon = True
    thread.start()
    
    # Add progress logging
    import time
    check_interval = 30  # Check every 30 seconds
    elapsed = 0
    while thread.is_alive() and elapsed < timeout_seconds:
        thread.join(check_interval)
        elapsed += check_interval
        if thread.is_alive():
            print(f"[Progress] API call still running... ({elapsed}s / {timeout_seconds}s)")
    
    if thread.is_alive():
        raise TimeoutError(f"Function timed out after {timeout_seconds} seconds")
    
    if exception[0]:
        raise exception[0]
    
    return result[0]


def check_gemini_available() -> bool:
    """Check if Gemini API is available.
    
    Returns:
        True if GEMINI_API_KEY is set
    """
    return 'GEMINI_API_KEY' in os.environ


def extract_text_from_image_gemini(image_data: bytes, mime_type: str = 'image/png') -> str:
    """Extract text from an image using Google Gemini Vision API.
    
    Args:
        image_data: The image file as bytes
        mime_type: MIME type of the image (e.g., 'image/png', 'image/jpeg')
        
    Returns:
        Extracted text from the image
        
    Raises:
        RuntimeError: If Gemini API is not available
    """
    if not check_gemini_available():
        raise RuntimeError(
            "GEMINI_API_KEY is not set. "
            "Please set it in your .env file or environment variables."
        )
    
    try:
        import google.generativeai as genai
        
        # Configure API
        api_key = os.environ.get('GEMINI_API_KEY')
        genai.configure(api_key=api_key)
        
        # Try different Gemini models that support vision
        model_names = [
            'models/gemini-1.5-flash',
            'models/gemini-1.5-pro',
            'models/gemini-pro-vision',
            'models/gemini-2.0-flash-exp'
        ]
        
        prompt = """Extract all the text from this image of a syllabus or course schedule. 
Return only the raw text content, preserving the structure and formatting as much as possible.
Include all dates, times, events, assignments, and important information."""
        
        for model_name in model_names:
            try:
                model = genai.GenerativeModel(model_name)
                
                # Configure for text extraction
                generation_config = {
                    "temperature": 0.1,
                    "top_p": 0.8,
                    "top_k": 40,
                    "max_output_tokens": 8192,
                }
                
                # Prepare the image
                image_pil = Image.open(io.BytesIO(image_data))
                
                # Resize image if too large (Gemini has size limits)
                MAX_DIMENSION = 1536  # Gemini's recommended max
                if image_pil.width > MAX_DIMENSION or image_pil.height > MAX_DIMENSION:
                    print(f"Resizing image from {image_pil.size} to fit within {MAX_DIMENSION}x{MAX_DIMENSION}")
                    image_pil.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)
                
                # Generate content with image
                response = model.generate_content(
                    [prompt, image_pil],
                    generation_config=generation_config
                )
                
                return response.text
                
            except Exception as e:
                print(f"Model {model_name} failed: {e}")
                continue
        
        raise Exception("All Gemini vision models failed")
        
    except Exception as e:
        raise RuntimeError(f"Failed to extract text from image using Gemini: {str(e)}")


def extract_events_from_image_gemini(image_data: bytes, mime_type: str = 'image/png') -> List[Dict]:
    """Extract events directly from an image using Google Gemini Vision API.
    
    This uses Gemini's vision capabilities to understand the image and extract
    calendar events directly, which is more accurate than OCR + text parsing.
    
    Args:
        image_data: The image file as bytes
        mime_type: MIME type of the image
        
    Returns:
        List of extracted events
    """
    import time
    from datetime import datetime, timedelta
    start_time = time.time()
    print("=" * 60)
    print("Starting image processing with Gemini Vision...")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    if not check_gemini_available():
        raise RuntimeError(
            "GEMINI_API_KEY is not set. "
            "Please set it in your .env file or environment variables."
        )
    
    try:
        import google.generativeai as genai
        import json
        import dateparser
        
        print("Gemini API key found, configuring API...")
        
        # Configure API
        api_key = os.environ.get('GEMINI_API_KEY')
        genai.configure(api_key=api_key)
        
        print("API configured successfully")
        
        # Build the prompt for event extraction (same as text processing)
        current_date = datetime.now().isoformat()
        prompt = f"""You are an expert at extracting calendar events from academic syllabi and course schedules.

Extract all events, deadlines, exams, lectures, and important dates from this image. The same event can be referenced in various parts of the document, each with some context. Make sure to group these events if you are sure they are the same

STEPS
- SCAN: Initially go through the image and note important names that refer to events or tasks, make sure to get anything academically related
- COLLECT: Collect info about events, grouping them by their names (make sure to distinguish separate midterms)
- COLLECT A SECOND TIME QUICKLY: make sure to not make duplicates
- OUTPUT: Output the events with enough info about them to be able to create a simple google calendar event

CLASSIFY each item as either an "event" or "task":
- EVENTS: Have specific start and end times (lectures, labs, discussions, exams, meetings, office hours)
- TASKS: Only have due dates, no specific time needed (assignments, projects, homework, papers)

Return a JSON array. Each item should have:
- type: Either "event" or "task"
- title: A short, descriptive title, do not include the date or time
- start_text: The exact start date/time mentioned (keep original format) OR due date for tasks
- end_text: The exact end date/time mentioned, or "1 hour" for events, "0" for tasks
- location: Building name, room number, or "Online" if mentioned (usually empty for tasks)
- description: For recurring events/tasks, include days of week (e.g., "Lecture MWF", "Lab TTH", "Assignment Monday"). For non-recurring: Category like "Lecture", "Lab", "Exam", "Discussion", "Assignment", "Project"
- recurring: Boolean indicating if this event/task recurs (e.g., weekly lectures, weekly assignments, recurring meetings). Events/tasks for which there is not specified date but there is a day of the week (or multiple ex: M W (Every Monday and Wednesday)) are likely to be recurring

Important rules:
1. Use the text's actual date formats (don't convert to ISO unless necessary)
2. For events without time, assume reasonable defaults (10am for classes, 3pm for exams)
3. For tasks, use the due date as start_text and set end_text to "0"
4. For recurring events or tasks, include days in description (e.g., "MWF", "TTH", "Monday Wednesday Friday", "Assignment Monday") so the recurrence pattern can be determined
5. Return ONLY valid JSON, no markdown formatting
6. Minimum event/task details: name, time, date

Current date context: {current_date}

Return JSON array:"""
        
        # Use models that explicitly support vision
        model_names = [
            'models/gemini-2.5-flash',  # Latest flash model
            'models/gemini-2.0-flash',   # Stable flash model
            'models/gemini-flash-latest', # Compatible version
            'models/gemini-pro-latest',   # Pro version
            'models/gemini-2.5-pro'       # Latest pro model
        ]
        
        print(f"Preparing image (size: {len(image_data)} bytes)...")
        image_pil = Image.open(io.BytesIO(image_data))
        print(f"Image loaded successfully: {image_pil.size}")
        
        # Resize image if too large (Gemini has size limits)
        MAX_DIMENSION = 1536  # Gemini's recommended max
        if image_pil.width > MAX_DIMENSION or image_pil.height > MAX_DIMENSION:
            print(f"Resizing image from {image_pil.size} to fit within {MAX_DIMENSION}x{MAX_DIMENSION}")
            image_pil.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)
            print(f"Image resized to: {image_pil.size}")
        
        response = None
        for model_name in model_names:
            try:
                print(f"Trying model: {model_name}...")
                model = genai.GenerativeModel(model_name)
                
                # Configure for structured output
                generation_config = {
                    "temperature": 0.1,
                    "top_p": 0.8,
                    "top_k": 40,
                    "max_output_tokens": 8192,
                }
                
                print(f"Sending request to {model_name}...")
                
                # Generate content with image (with timeout handling)
                try:
                    # Wrap in a timeout function (5 minutes = 300 seconds)
                    def call_api():
                        print(f"API call started at {datetime.now().strftime('%H:%M:%S')}")
                        return model.generate_content(
                            [prompt, image_pil],
                            generation_config=generation_config
                        )
                    
                    print(f"Starting API call with timeout of 300 seconds (5 minutes)...")
                    api_start_time = datetime.now()
                    response = timeout_handler(call_api, timeout_seconds=300)
                    elapsed = (datetime.now() - api_start_time).total_seconds()
                    print(f"Successfully got response from {model_name} after {elapsed:.1f} seconds")
                    break
                except TimeoutError as timeout_err:
                    print(f"Timeout with {model_name}: {timeout_err}")
                    continue
                except Exception as api_error:
                    print(f"API error with {model_name}: {api_error}")
                    # Check if it's a timeout or rate limit
                    if "timeout" in str(api_error).lower() or "429" in str(api_error):
                        print(f"Rate limit or timeout with {model_name}, trying next model...")
                        continue
                    raise  # Re-raise if it's a different error
                
            except Exception as model_error:
                print(f"Model {model_name} failed: {model_error}")
                continue
        
        if response is None:
            raise Exception("All Gemini vision models failed")
        
        print("Received response, parsing...")
        
        # Extract JSON from response
        response_text = response.text
        print(f"Response length: {len(response_text)} characters")
        
        # Clean up the response (remove markdown code blocks if present)
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        print("Cleaned response, parsing JSON...")
        
        # Parse JSON (dateparser and timedelta already imported above)
        events_raw = json.loads(response_text.strip())
        print(f"Parsed {len(events_raw)} events from JSON")
        
        # Convert to our format with proper datetime objects
        events = []
        for idx, event_raw in enumerate(events_raw):
            try:
                event_type = event_raw.get('type', 'event')
                
                # Parse start time
                start_text = event_raw.get('start_text', '')
                start_dt = dateparser.parse(start_text, settings={"PREFER_DATES_FROM": "future"})
                
                if not start_dt:
                    continue  # Skip if we can't parse the date
                
                # Handle events vs tasks differently
                if event_type == 'task':
                    # Tasks are all-day events
                    end_dt = start_dt
                else:
                    # Parse end time for events
                    end_text = event_raw.get('end_text', '1 hour')
                    if end_text == '0' or end_text.lower() == 'none':
                        end_dt = start_dt  # All-day event
                    elif 'hour' in end_text.lower() or 'hr' in end_text.lower():
                        # Extract number of hours
                        try:
                            hours = float(''.join(filter(str.isdigit, end_text.split()[0])))
                            end_dt = start_dt + timedelta(hours=hours)
                        except:
                            end_dt = start_dt + timedelta(hours=1)
                    else:
                        end_dt = dateparser.parse(end_text, settings={"PREFER_DATES_FROM": "future"})
                        if not end_dt:
                            end_dt = start_dt + timedelta(hours=1)
                
                # Get recurring flag (can be True for both events and tasks)
                recurring = event_raw.get('recurring', False)
                
                event = {
                    "title": event_raw.get('title', 'Event'),
                    "start": start_dt,
                    "end": end_dt,
                    "description": event_raw.get('description', ''),
                    "location": event_raw.get('location'),
                    "type": event_type,
                    "all_day": (event_type == 'task' or end_dt == start_dt),
                    "recurring": recurring
                }
                events.append(event)
                recurring_status = "♻️ Recurring" if recurring else "One-time"
                print(f"Successfully parsed event {idx + 1}/{len(events_raw)}: {event['title']} ({recurring_status})")
            except Exception as e:
                print(f"Error parsing event {idx + 1}: {e}")
                continue
        
        total_time = time.time() - start_time
        print("=" * 60)
        print(f"Successfully processed {len(events)} events from image")
        print(f"Total processing time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
        print(f"End time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        return events
        
    except Exception as e:
        total_time = time.time() - start_time
        print("=" * 60)
        print(f"ERROR: Failed after {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
        print(f"Error: {str(e)}")
        print("=" * 60)
        raise RuntimeError(f"Failed to extract events from image using Gemini: {str(e)}")


def process_image_file(file_path: str) -> str:
    """Extract text from an image file using Gemini Vision.
    
    Args:
        file_path: Path to the image file
        
    Returns:
        Extracted text from the image
    """
    with open(file_path, 'rb') as f:
        image_data = f.read()
    
    # Determine MIME type from file extension
    ext = file_path.lower().split('.')[-1]
    mime_types = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'bmp': 'image/bmp',
        'webp': 'image/webp'
    }
    mime_type = mime_types.get(ext, 'image/png')
    
    return extract_text_from_image_gemini(image_data, mime_type)


def extract_events_from_image(image_path: str) -> List[Dict]:
    """Extract events from an image file using Gemini Vision.
    
    This is the main function to use - it extracts events directly from images.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        List of extracted events
    """
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    # Determine MIME type from file extension
    ext = image_path.lower().split('.')[-1]
    mime_types = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'gif': 'image/gif',
        'bmp': 'image/bmp',
        'webp': 'image/webp'
    }
    mime_type = mime_types.get(ext, 'image/png')
    
    return extract_events_from_image_gemini(image_data, mime_type)


def extract_events_from_image_bytes(image_data: bytes, mime_type: str = 'image/png') -> List[Dict]:
    """Extract events from image data (bytes) using Gemini Vision.
    
    Args:
        image_data: The image file as bytes
        mime_type: MIME type of the image
        
    Returns:
        List of extracted events
    """
    return extract_events_from_image_gemini(image_data, mime_type)


def get_supported_image_formats() -> tuple:
    """Get supported image formats for Gemini Vision.
    
    Returns:
        Tuple of supported file extensions
    """
    return ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')


if __name__ == "__main__":
    # Test the Gemini Vision functionality
    print("Testing image processor with Gemini Vision...")
    
    if check_gemini_available():
        print("✓ Gemini API is available")
    else:
        print("✗ Gemini API is not available. Please set GEMINI_API_KEY in your environment")
    
    print(f"Supported formats: {get_supported_image_formats()}")

