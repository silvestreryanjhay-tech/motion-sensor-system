from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from datetime import datetime
import json
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import threading
import schedule
import time
from motion_detector import MotionDetector
from camera_handler import CameraHandler
from notification import NotificationService
from buzzer_control import BuzzerControl

load_dotenv()

app = Flask(__name__)
CORS(app)

# Initialize Supabase
supabase: Client = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

# Initialize components
motion_detector = MotionDetector()
camera_handler = CameraHandler()
notification_service = NotificationService()
buzzer = BuzzerControl()

# Global variables
is_system_active = True
motion_detected = False
current_status = {
    'motion': False,
    'camera_active': False,
    'buzzer_active': False,
    'last_detection': None
}

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current system status"""
    return jsonify({
        'status': 'active' if is_system_active else 'inactive',
        'motion_detected': current_status['motion'],
        'camera_active': current_status['camera_active'],
        'buzzer_active': current_status['buzzer_active'],
        'last_detection': current_status['last_detection']
    })

@app.route('/api/toggle', methods=['POST'])
def toggle_system():
    """Toggle system on/off"""
    global is_system_active
    data = request.json
    is_system_active = data.get('active', True)
    return jsonify({'success': True, 'active': is_system_active})

@app.route('/api/events', methods=['GET'])
def get_events():
    """Get motion events from database"""
    try:
        response = supabase.table('motion_events')\
            .select('*')\
            .order('timestamp', desc=True)\
            .limit(50)\
            .execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get statistics for dashboard"""
    try:
        # Get today's events
        today = datetime.now().date().isoformat()
        response = supabase.table('motion_events')\
            .select('*')\
            .gte('timestamp', f'{today}T00:00:00')\
            .execute()
        
        events = response.data
        hourly_data = [0] * 24
        for event in events:
            hour = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00')).hour
            hourly_data[hour] += 1
        
        return jsonify({
            'total_events': len(events),
            'hourly_distribution': hourly_data,
            'latest_events': events[:10]
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/image/<filename>', methods=['GET'])
def get_image(filename):
    """Serve captured images"""
    image_path = f'captured_images/{filename}'
    if os.path.exists(image_path):
        return send_file(image_path, mimetype='image/jpeg')
    return jsonify({'error': 'Image not found'}), 404

def motion_callback():
    """Callback when motion is detected"""
    global current_status, motion_detected
    
    if not is_system_active:
        return
    
    print("Motion detected!")
    current_status['motion'] = True
    current_status['last_detection'] = datetime.now().isoformat()
    
    # Activate buzzer
    buzzer.activate()
    current_status['buzzer_active'] = True
    
    # Capture image
    image_path = camera_handler.capture_image()
    if image_path:
        current_status['camera_active'] = True
    
    # Record video (5 seconds)
    video_path = camera_handler.record_video(duration=5)
    
    # Save to database
    event_data = {
        'timestamp': datetime.now().isoformat(),
        'image_path': os.path.basename(image_path) if image_path else None,
        'video_path': os.path.basename(video_path) if video_path else None,
        'motion_detected': True
    }
    
    try:
        supabase.table('motion_events').insert(event_data).execute()
    except Exception as e:
        print(f"Error saving to database: {e}")
    
    # Send notification
    notification_service.send_email(
        subject="Motion Detected!",
        body=f"Motion was detected at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        image_path=image_path
    )
    
    # Deactivate buzzer after 2 seconds
    threading.Timer(2.0, lambda: buzzer.deactivate()).start()
    
    # Reset status after 5 seconds
    threading.Timer(5.0, lambda: reset_status()).start()

def reset_status():
    """Reset system status"""
    global current_status
    current_status['motion'] = False
    current_status['camera_active'] = False
    current_status['buzzer_active'] = False

def start_motion_detection():
    """Start the motion detection thread"""
    while True:
        if is_system_active:
            if motion_detector.detect_motion():
                motion_callback()
        time.sleep(0.5)

if __name__ == '__main__':
    # Start motion detection in background thread
    detection_thread = threading.Thread(target=start_motion_detection, daemon=True)
    detection_thread.start()
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)