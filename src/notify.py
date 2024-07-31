import adafruit_requests
import binascii
import os

class TwilioNotifier:
    def __init__(self, requests: adafruit_requests.Session):
        self.requests: adafruit_requests.Session = requests
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID", "")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN", "")
        self.from_number = os.getenv("TWILIO_PHONE_NUMBER", "")
        self.to_number = os.getenv("TWILIO_DESTINATION_PHONE_NUMBER", "")

    def send_alert(self, message):
        """Send a message via Twilio."""
        # URL for the Twilio API
        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"

        # Create the authorization header
        auth_str = f"{self.account_sid}:{self.auth_token}"
        auth_bytes = auth_str.encode("utf-8")
        auth_base64 = binascii.b2a_base64(auth_bytes).decode("utf-8").strip()

        headers = {
            "Authorization": f"Basic {auth_base64}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # Message data
        data = {
            "From": self.from_number,
            "To": self.to_number,
            "Body": message,
        }

        # Send the POST request
        response = self.requests.post(url, headers=headers, data=data)

        # Check the response status code
        if response.status_code != 201:
            error_details = response.text
            print("Received response error code:", response.status_code)
            print("Error details:", error_details)
            print("Response headers:", response.headers)
            raise Exception(f"Failed to send message: {error_details}")
        else:
            print(f"Alert successfully sent to {self.to_number}: '{message}'")
