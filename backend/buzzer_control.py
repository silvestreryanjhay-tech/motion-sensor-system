import RPi.GPIO as GPIO
import time

class BuzzerControl:
    def __init__(self, pin=18):
        self.pin = pin
        self.setup_gpio()
    
    def setup_gpio(self):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        self.pwm = GPIO.PWM(self.pin, 1000)  # 1kHz frequency
        self.pwm.start(0)
    
    def activate(self, frequency=1000, duration=None):
        """Activate buzzer with specific frequency"""
        self.pwm.ChangeFrequency(frequency)
        self.pwm.ChangeDutyCycle(50)  # 50% duty cycle
        
        if duration:
            time.sleep(duration)
            self.deactivate()
    
    def deactivate(self):
        """Deactivate buzzer"""
        self.pwm.ChangeDutyCycle(0)
    
    def beep_pattern(self, pattern):
        """Beep in a pattern (e.g., [0.5, 0.5, 1.0])"""
        for duration in pattern:
            self.activate(duration=duration)
            time.sleep(0.1)
    
    def cleanup(self):
        self.pwm.stop()
        GPIO.cleanup(self.pin)