import random
import requests
from django.conf import settings


# ================= OTP GENERATOR =================
def generate_otp():
    """
    Generate 6 digit numeric OTP
    """
    return str(random.randint(100000, 999999))


# ================= SEND OTP VIA FAST2SMS =================
def send_otp_sms(mobile, otp):
    """
    Send OTP using FAST2SMS OTP route (DLT compliant)
    """

    url = "https://www.fast2sms.com/dev/bulkV2"

    payload = {
        "route": "otp",                 # MUST be otp
        "variables_values": str(otp),   # ONLY OTP value
        "numbers": str(mobile)          # 10 digit mobile number
    }

    headers = {
        "authorization": settings.FAST2SMS_API_KEY,
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print("📨 FAST2SMS RESPONSE:", response.text)
        return response.json()

    except Exception as e:
        print("❌ FAST2SMS ERROR:", e)
        return None


# ================= DEVICE LOCK =================
def get_device_id(request):
    """
    Create simple device fingerprint
    """
    user_agent = request.META.get("HTTP_USER_AGENT", "")
    ip = request.META.get("REMOTE_ADDR", "")
    return f"{user_agent}_{ip}"
