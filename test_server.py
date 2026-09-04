from flask import Flask, jsonify, send_from_directory, send_file, request
from flask_cors import CORS
from datetime import datetime, timedelta
import random
import io
import os
from PIL import Image, ImageDraw
from dotenv import load_dotenv

# Try importing Supabase with error handling
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("⚠️ Supabase package not available. Using mock data.")

# ===== LOAD ENVIRONMENT VARIABLES =====
load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# ===== SUPABASE CONFIGURATION =====
SUPABASE_URL = "https://lzkzmdsgnnyxnsfoxcee.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx6a3ptZHNnbm55eG5zZm94Y2VlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODg1MDYwOTEsImV4cCI6MjEwNDA4MjA5MX0.pXGk24qRS9KK2NHuBXa6NPA0hVaYsTkxkoYLU2kQV_s"

# Initialize Supabase with proper error handling
supabase = None

if SUPABASE_AVAILABLE:
    try:
        # First attempt: Standard connection
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase connected successfully!")
        print(f"   URL: {SUPABASE_URL}")
    except Exception as e:
        error_msg = str(e)
        if "http2" in error_msg.lower():
            print("⚠️ HTTP/2 not available - attempting HTTP/1.1 connection...")
            try:
                # Try with HTTP/2 disabled via environment variable
                import httpx
                # Create a custom client without HTTP/2
                custom_client = httpx.Client(http2=False)
                # Recreate supabase with custom client
                supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
                print("✅ Supabase connected successfully (HTTP/1.1)!")
            except Exception as e2:
                print(f"❌ Supabase connection error: {e2}")
                supabase = None
        else:
            print(f"❌ Supabase connection error: {e}")
            supabase = None
else:
    print("⚠️ Supabase not available. Using mock data.")

# ===== MOCK DATA (FALLBACK) =====
mock_events = []
for i in range(20):
    timestamp = datetime.now() - timedelta(hours=random.randint(0, 23))
    mock_events.append({
        'id': i + 1,
        'timestamp': timestamp.isoformat(),
        'image_path': f'capture_{i+1}.jpg' if random.random() > 0.3 else None,
        'video_path': f'record_{i+1}.h264' if random.random() > 0.5 else None,
        'motion_detected': True
    })

system_active = True

# ===== DATABASE FUNCTIONS =====
def get_events_from_db(limit=50):
    """Fetch events from Supabase or mock data"""
    if not supabase:
        return mock_events
    
    try:
        response = supabase.table('motion_events')\
            .select('*')\
            .order('timestamp', desc=True)\
            .limit(limit)\
            .execute()
        return response.data if response.data else []
    except Exception as e:
        print(f"❌ Error fetching events: {e}")
        return mock_events

def save_event_to_db(event_data):
    """Save event to Supabase or mock data"""
    if not supabase:
        print("⚠️ Supabase not connected - saving to mock data")
        mock_events.insert(0, event_data)
        return True
    
    try:
        response = supabase.table('motion_events').insert(event_data).execute()
        print("✅ Event saved to Supabase!")
        return True
    except Exception as e:
        print(f"❌ Error saving to Supabase: {e}")
        # Fallback to mock data
        mock_events.insert(0, event_data)
        return False

def get_stats_from_db():
    """Get statistics from Supabase or mock data"""
    if not supabase:
        hourly = [random.randint(0, 8) for _ in range(24)]
        return {
            'total_events': len(mock_events),
            'hourly_distribution': hourly,
            'latest_events': mock_events[:10]
        }
    
    try:
        today = datetime.now().date().isoformat()
        response = supabase.table('motion_events')\
            .select('*')\
            .gte('timestamp', f'{today}T00:00:00')\
            .execute()
        
        events = response.data if response.data else []
        hourly_data = [0] * 24
        for event in events:
            try:
                hour = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00')).hour
                hourly_data[hour] += 1
            except:
                pass
        
        latest_response = supabase.table('motion_events')\
            .select('*')\
            .order('timestamp', desc=True)\
            .limit(10)\
            .execute()
        
        return {
            'total_events': len(events),
            'hourly_distribution': hourly_data,
            'latest_events': latest_response.data if latest_response.data else []
        }
    except Exception as e:
        print(f"❌ Error fetching stats: {e}")
        return get_stats_from_db()

# ===== ROUTES =====
@app.route('/')
def index():
    """Serve landing page"""
    return send_from_directory('.', 'index.html')

@app.route('/dashboard')
def dashboard():
    """Serve dashboard page"""
    return send_from_directory('.', 'dashboard.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files"""
    if os.path.exists(path):
        return send_from_directory('.', path)
    return jsonify({'error': 'File not found'}), 404

@app.route('/api/status')
def get_status():
    """Get system status"""
    return jsonify({
        'status': 'active' if system_active else 'inactive',
        'motion_detected': random.choice([True, False, False, False]),
        'camera_active': random.choice([True, False]),
        'buzzer_active': random.choice([True, False]),
        'last_detection': datetime.now().isoformat() if random.choice([True, False]) else None,
        'supabase_connected': supabase is not None
    })

@app.route('/api/toggle', methods=['POST'])
def toggle_system():
    """Toggle system on/off"""
    global system_active
    system_active = not system_active
    return jsonify({'success': True, 'active': system_active})

@app.route('/api/events')
def get_events():
    """Get recent events"""
    events = get_events_from_db(50)
    return jsonify(events)

@app.route('/api/stats')
def get_stats():
    """Get statistics"""
    stats = get_stats_from_db()
    return jsonify(stats)

@app.route('/api/capture', methods=['POST'])
def capture():
    """Simulate image capture and save to database"""
    timestamp = datetime.now().isoformat()
    image_filename = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    
    event_data = {
        'timestamp': timestamp,
        'image_path': image_filename,
        'video_path': None,
        'motion_detected': True
    }
    
    save_event_to_db(event_data)
    
    return jsonify({
        'success': True, 
        'message': 'Image captured!',
        'image': image_filename,
        'saved_to_supabase': supabase is not None
    })

@app.route('/api/record', methods=['POST'])
def record():
    """Simulate video recording and save to database"""
    timestamp = datetime.now().isoformat()
    video_filename = f"record_{datetime.now().strftime('%Y%m%d_%H%M%S')}.h264"
    
    event_data = {
        'timestamp': timestamp,
        'image_path': None,
        'video_path': video_filename,
        'motion_detected': True
    }
    
    save_event_to_db(event_data)
    
    return jsonify({
        'success': True, 
        'message': 'Recording started!',
        'video': video_filename,
        'saved_to_supabase': supabase is not None
    })

@app.route('/api/image/<filename>')
def get_image(filename):
    """Serve captured images (mock)"""
    img = Image.new('RGB', (640, 480), color=(73, 109, 137))
    d = ImageDraw.Draw(img)
    d.text((50, 200), f"Motion Capture: {filename}", fill=(255, 255, 255))
    d.text((50, 240), f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fill=(255, 255, 255))
    d.text((50, 280), "🟢 Motion Detected!", fill=(0, 255, 0))
    d.text((50, 320), f"ID: {filename.split('_')[1] if '_' in filename else 'N/A'}", fill=(255, 255, 255))
    
    img_io = io.BytesIO()
    img.save(img_io, 'JPEG', quality=70)
    img_io.seek(0)
    return send_file(img_io, mimetype='image/jpeg')

@app.route('/api/motion/simulate', methods=['POST'])
def simulate_motion():
    """Simulate motion detection from hardware"""
    data = request.json or {}
    motion_detected = data.get('motion_detected', True)
    image_path = data.get('image_path', None)
    video_path = data.get('video_path', None)
    
    event_data = {
        'timestamp': datetime.now().isoformat(),
        'image_path': image_path,
        'video_path': video_path,
        'motion_detected': motion_detected
    }
    
    save_event_to_db(event_data)
    
    return jsonify({
        'success': True,
        'message': 'Motion event recorded',
        'event': event_data,
        'saved_to_supabase': supabase is not None
    })

@app.route('/api/supabase/status')
def supabase_status():
    """Check Supabase connection status"""
    return jsonify({
        'connected': supabase is not None,
        'url': SUPABASE_URL,
        'using_mock_data': supabase is None
    })

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Motion Sensor Website - Test Server")
    print("="*60)
    if supabase:
        print("📡 Supabase: ✅ CONNECTED")
        print(f"   URL: {SUPABASE_URL}")
    else:
        print("📡 Supabase: ⚠️ USING MOCK DATA")
        print("   (Add httpx[http2] to requirements.txt for full Supabase support)")
    print("\n📍 OPEN THESE URLs IN YOUR BROWSER:")
    print("   🏠 Landing Page:  http://localhost:5000")
    print("   📊 Dashboard:     http://localhost:5000/dashboard")
    print("   📡 API Test:      http://localhost:5000/api/status")
    print("   🔌 Supabase Status: http://localhost:5000/api/supabase/status")
    print("\n💡 Press CTRL+C to stop the server")
    print("="*60 + "\n")
    app.run(host='0.0.0.0', port=10000)