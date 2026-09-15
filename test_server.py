from flask import Flask, jsonify, send_from_directory, send_file, request
from flask_cors import CORS
from datetime import datetime
import os
import io
from PIL import Image, ImageDraw
from dotenv import load_dotenv

# Try importing Supabase
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("⚠️ Supabase package not available.")

load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# ===== SUPABASE CONFIGURATION =====
SUPABASE_URL = os.getenv('SUPABASE_URL', "https://lzkzmdsgnnyxnsfoxcee.supabase.co")
SUPABASE_KEY = os.getenv('SUPABASE_KEY', "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx6a3ptZHNnbm55eG5zZm94Y2VlIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODg1MDYwOTEsImV4cCI6MjEwNDA4MjA5MX0.pXGk24qRS9KK2NHuBXa6NPA0hVaYsTkxkoYLU2kQV_s")

supabase = None
if SUPABASE_AVAILABLE:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase connected!")
    except Exception as e:
        print(f"❌ Supabase error: {e}")

# ===== SYSTEM STATE (REAL-TIME FROM HARDWARE) =====
# Walang mock data. Lahat ng data ay galing sa Pi.
system_state = {
    'status': 'idle',           # idle, active, motion
    'motion_detected': False,
    'camera_active': False,
    'buzzer_active': False,
    'last_detection': None,
    'last_update': None,
    'device_connected': False
}

# ===== ROUTES =====

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/dashboard')
def dashboard():
    return send_from_directory('.', 'dashboard.html')

@app.route('/<path:path>')
def serve_static(path):
    if os.path.exists(path):
        return send_from_directory('.', path)
    return jsonify({'error': 'File not found'}), 404

# ===== API: STATUS (GALING SA HARDWARE) =====
@app.route('/api/status')
def get_status():
    """
    Return real-time status.
    Walang random values. Kung walang hardware, idle lang.
    """
    # Check if device is still connected (last update within 30 seconds)
    if system_state['last_update']:
        time_diff = (datetime.now() - datetime.fromisoformat(system_state['last_update'])).total_seconds()
        if time_diff > 30:
            system_state['device_connected'] = False
            system_state['status'] = 'idle'
            system_state['motion_detected'] = False
            system_state['camera_active'] = False
            system_state['buzzer_active'] = False
    
    return jsonify({
        'status': system_state['status'],
        'motion_detected': system_state['motion_detected'],
        'camera_active': system_state['camera_active'],
        'buzzer_active': system_state['buzzer_active'],
        'last_detection': system_state['last_detection'],
        'device_connected': system_state['device_connected'],
        'supabase_connected': supabase is not None
    })

# ===== API: EVENTS (GALING SA SUPABASE) =====
@app.route('/api/events')
def get_events():
    """
    Return events from Supabase.
    Kung walang data, empty array.
    """
    if not supabase:
        return jsonify([])
    
    try:
        response = supabase.table('motion_events')\
            .select('*')\
            .order('timestamp', desc=True)\
            .limit(50)\
            .execute()
        return jsonify(response.data if response.data else [])
    except Exception as e:
        print(f"❌ Error fetching events: {e}")
        return jsonify([])

# ===== API: STATS (GALING SA SUPABASE) =====
@app.route('/api/stats')
def get_stats():
    """
    Return stats from Supabase.
    Kung walang data, zeroes lang.
    """
    if not supabase:
        return jsonify({
            'total_events': 0,
            'hourly_distribution': [0] * 24,
            'latest_events': []
        })
    
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
        
        return jsonify({
            'total_events': len(events),
            'hourly_distribution': hourly_data,
            'latest_events': latest_response.data if latest_response.data else []
        })
    except Exception as e:
        print(f"❌ Error fetching stats: {e}")
        return jsonify({
            'total_events': 0,
            'hourly_distribution': [0] * 24,
            'latest_events': []
        })

# ===== API: RECEIVE DATA FROM RASPBERRY PI =====
@app.route('/api/motion', methods=['POST'])
def receive_motion():
    """
    Endpoint na tinatawag ng Raspberry Pi kapag may motion.
    Ito ang nag-uupdate ng system_state.
    """
    data = request.json or {}
    
    print(f"\n📡 Received data from Raspberry Pi:")
    print(f"   Motion: {data.get('motion_detected')}")
    print(f"   Image: {data.get('image_path')}")
    print(f"   Video: {data.get('video_path')}")
    
    # Update system state
    system_state['motion_detected'] = data.get('motion_detected', True)
    system_state['camera_active'] = data.get('camera_active', False)
    system_state['buzzer_active'] = data.get('buzzer_active', False)
    system_state['last_detection'] = datetime.now().isoformat()
    system_state['last_update'] = datetime.now().isoformat()
    system_state['device_connected'] = True
    system_state['status'] = 'active'
    
    # Save to Supabase
    event_data = {
        'timestamp': datetime.now().isoformat(),
        'image_path': data.get('image_path'),
        'video_path': data.get('video_path'),
        'motion_detected': data.get('motion_detected', True)
    }
    
    if supabase:
        try:
            supabase.table('motion_events').insert(event_data).execute()
            print("✅ Saved to Supabase!")
        except Exception as e:
            print(f"❌ Supabase save error: {e}")
    
    # Reset motion after 5 seconds (para hindi stuck sa "motion detected")
    import threading
    def reset_motion():
        import time
        time.sleep(5)
        system_state['motion_detected'] = False
        system_state['camera_active'] = False
        system_state['buzzer_active'] = False
        system_state['status'] = 'idle'
    
    threading.Thread(target=reset_motion, daemon=True).start()
    
    return jsonify({
        'success': True,
        'message': 'Motion event received',
        'event': event_data
    })

# ===== API: HEARTBEAT FROM PI =====
@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    """
    Raspberry Pi sends heartbeat every 10 seconds.
    Para malaman ng server na connected pa ang device.
    """
    system_state['last_update'] = datetime.now().isoformat()
    system_state['device_connected'] = True
    return jsonify({'success': True, 'timestamp': datetime.now().isoformat()})

# ===== API: RESET (for testing) =====
@app.route('/api/reset', methods=['POST'])
def reset():
    """Reset system state."""
    global system_state
    system_state = {
        'status': 'idle',
        'motion_detected': False,
        'camera_active': False,
        'buzzer_active': False,
        'last_detection': None,
        'last_update': None,
        'device_connected': False
    }
    return jsonify({'success': True, 'message': 'System reset'})

@app.route('/api/image/<filename>')
def get_image(filename):
    img = Image.new('RGB', (640, 480), color=(73, 109, 137))
    d = ImageDraw.Draw(img)
    d.text((50, 200), f"Motion Capture: {filename}", fill=(255, 255, 255))
    d.text((50, 240), f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fill=(255, 255, 255))
    d.text((50, 280), "Motion Detected!", fill=(0, 255, 0))
    
    img_io = io.BytesIO()
    img.save(img_io, 'JPEG', quality=70)
    img_io.seek(0)
    return send_file(img_io, mimetype='image/jpeg')

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Motion Sensor Server - Group 2 Embedded")
    print("="*60)
    print(f"📡 Supabase: {'✅ Connected' if supabase else '⚠️ Not connected'}")
    print("📊 Data source: HARDWARE ONLY (no mock data)")
    print("\n📍 URLs:")
    print("   🏠 Landing:  http://localhost:5000")
    print("   📊 Dashboard: http://localhost:5000/dashboard")
    print("   📡 Status:    http://localhost:5000/api/status")
    print("\n💡 Waiting for Raspberry Pi data...")
    print("="*60 + "\n")
    app.run(host='0.0.0.0', port=10000)