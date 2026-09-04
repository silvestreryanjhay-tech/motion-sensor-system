from flask import Flask, jsonify, send_from_directory, send_file
from flask_cors import CORS
from datetime import datetime, timedelta
import random
import io
from PIL import Image, ImageDraw

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

# Mock events data
events = []
for i in range(20):
    timestamp = datetime.now() - timedelta(hours=random.randint(0, 23))
    events.append({
        'id': i + 1,
        'timestamp': timestamp.isoformat(),
        'image_path': f'capture_{i+1}.jpg',
        'video_path': f'record_{i+1}.h264' if i % 2 == 0 else None,
        'motion_detected': True
    })

system_active = True

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/dashboard')
def dashboard():
    return send_from_directory('.', 'dashboard.html')

@app.route('/api/status')
def get_status():
    return jsonify({
        'status': 'active' if system_active else 'inactive',
        'motion_detected': random.choice([True, False, False, False]),
        'camera_active': random.choice([True, False]),
        'buzzer_active': random.choice([True, False]),
        'last_detection': datetime.now().isoformat() if random.choice([True, False]) else None
    })

@app.route('/api/toggle', methods=['POST'])
def toggle_system():
    global system_active
    system_active = not system_active
    return jsonify({'success': True, 'active': system_active})

@app.route('/api/events')
def get_events():
    return jsonify(events)

@app.route('/api/stats')
def get_stats():
    hourly = [random.randint(0, 8) for _ in range(24)]
    return jsonify({
        'total_events': len(events),
        'hourly_distribution': hourly,
        'latest_events': events[:10]
    })

@app.route('/api/capture', methods=['POST'])
def capture():
    return jsonify({'success': True, 'message': 'Image captured!'})

@app.route('/api/record', methods=['POST'])
def record():
    return jsonify({'success': True, 'message': 'Recording started!'})

@app.route('/api/image/<filename>')
def get_image(filename):
    img = Image.new('RGB', (640, 480), color=(73, 109, 137))
    d = ImageDraw.Draw(img)
    d.text((50, 200), f"Motion Capture: {filename}", fill=(255, 255, 255))
    d.text((50, 240), f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fill=(255, 255, 255))
    d.text((50, 280), "🟢 Motion Detected!", fill=(0, 255, 0))
    
    img_io = io.BytesIO()
    img.save(img_io, 'JPEG', quality=70)
    img_io.seek(0)
    return send_file(img_io, mimetype='image/jpeg')

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 Motion Sensor Website - Test Server")
    print("="*60)
    print("\n📍 OPEN THESE URLs IN YOUR BROWSER:")
    print("   🏠 Landing Page:  http://localhost:5000")
    print("   📊 Dashboard:     http://localhost:5000/dashboard")
    print("   📡 API Test:      http://localhost:5000/api/status")
    print("\n💡 Press CTRL+C to stop the server")
    print("="*60 + "\n")
    app.run(host='0.0.0.0', port=10000)
