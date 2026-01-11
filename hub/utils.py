import random
import requests
from django.conf import settings


# ================= OTP GENERATOR =================
def generate_otp():
    return str(random.randint(100000, 999999))


# ================= SEND OTP VIA FAST2SMS =================
def send_otp_sms(mobile, otp):
    url = "https://www.fast2sms.com/dev/bulkV2"

    payload = {
        "route": "otp",
        "variables_values": otp,
        "numbers": mobile
    }

    headers = {
        "authorization": settings.FAST2SMS_API_KEY,
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers)
    print("FAST2SMS RESPONSE:", response.text)

    


# ================= DEVICE LOCK =================
def get_device_id(request):
    user_agent = request.META.get("HTTP_USER_AGENT", "")
    ip = request.META.get("REMOTE_ADDR", "")
    return f"{user_agent}_{ip}"

