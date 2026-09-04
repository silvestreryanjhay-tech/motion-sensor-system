import RPi.GPIO as GPIO
import time

class MotionDetector:
    def __init__(self, pin=17):
        self.pin = pin
        self.setup_gpio()
    
    def setup_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN)
    
    def detect_motion(self):
        """Returns True if motion is detected"""
        return GPIO.input(self.pin) == GPIO.HIGH
    
    def cleanup(self):
        GPIO.cleanup()