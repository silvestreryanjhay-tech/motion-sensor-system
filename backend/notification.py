import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import os
from dotenv import load_dotenv
import requests

load_dotenv()

class NotificationService:
    def __init__(self):
        self.email_sender = os.getenv('EMAIL_SENDER')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.recipient_email = os.getenv('RECIPIENT_EMAIL')
        
        # For SMS using Twilio (optional)
        self.twilio_account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.twilio_auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.twilio_phone_number = os.getenv('TWILIO_PHONE_NUMBER')
        self.recipient_phone = os.getenv('RECIPIENT_PHONE')
    
    def send_email(self, subject, body, image_path=None):
        """Send email notification with optional image attachment"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_sender
            msg['To'] = self.recipient_email
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            if image_path and os.path.exists(image_path):
                with open(image_path, 'rb') as f:
                    img = MIMEImage(f.read())
                    img.add_header('Content-Disposition', 'attachment', 
                                 filename=os.path.basename(image_path))
                    msg.attach(img)
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(self.email_sender, self.email_password)
            server.send_message(msg)
            server.quit()
            
            print("Email notification sent successfully!")
            return True
            
        except Exception as e:
            print(f"Email sending error: {e}")
            return False
    
    def send_sms(self, message):
        """Send SMS notification using Twilio"""
        if not all([self.twilio_account_sid, self.twilio_auth_token, 
                   self.twilio_phone_number, self.recipient_phone]):
            print("SMS not configured")
            return False
        
        try:
            from twilio.rest import Client
            client = Client(self.twilio_account_sid, self.twilio_auth_token)
            
            client.messages.create(
                body=message,
                from_=self.twilio_phone_number,
                to=self.recipient_phone
            )
            print("SMS sent successfully!")
            return True
            
        except Exception as e:
            print(f"SMS sending error: {e}")
            return False
    
    def send_push_notification(self, title, body):
        """Send push notification using Pushbullet or similar service"""
        # Example with Pushbullet
        api_key = os.getenv('PUSHBULLET_API_KEY')
        if not api_key:
            print("Push notification not configured")
            return False
        
        try:
            url = 'https://api.pushbullet.com/v2/pushes'
            headers = {
                'Access-Token': api_key,
                'Content-Type': 'application/json'
            }
            data = {
                'type': 'note',
                'title': title,
                'body': body
            }
            response = requests.post(url, headers=headers, json=data)
            return response.status_code == 200
        except Exception as e:
            print(f"Push notification error: {e}")
            return False