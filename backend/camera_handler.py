from picamera2 import Picamera2
import time
import os
from datetime import datetime

class CameraHandler:
    def __init__(self):
        self.camera = None
        self.setup_camera()
        self.create_directories()
    
    def setup_camera(self):
        try:
            self.camera = Picamera2()
            config = self.camera.create_still_configuration()
            self.camera.configure(config)
            self.camera.start()
            time.sleep(2)  # Camera warm-up
        except Exception as e:
            print(f"Camera initialization error: {e}")
    
    def create_directories(self):
        os.makedirs('captured_images', exist_ok=True)
        os.makedirs('captured_videos', exist_ok=True)
    
    def capture_image(self):
        """Capture and save image"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'captured_images/motion_{timestamp}.jpg'
            self.camera.capture_file(filename)
            return filename
        except Exception as e:
            print(f"Image capture error: {e}")
            return None
    
    def record_video(self, duration=5):
        """Record video for specified duration"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'captured_videos/motion_{timestamp}.h264'
            
            # Configure video
            video_config = self.camera.create_video_configuration()
            self.camera.configure(video_config)
            self.camera.start()
            
            self.camera.start_recording(filename)
            time.sleep(duration)
            self.camera.stop_recording()
            
            # Switch back to still configuration
            still_config = self.camera.create_still_configuration()
            self.camera.configure(still_config)
            self.camera.start()
            
            return filename
        except Exception as e:
            print(f"Video recording error: {e}")
            return None
    
    def cleanup(self):
        if self.camera:
            self.camera.stop()
            self.camera.close()