from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponseForbidden
from django.conf import settings
from django.views.decorators.http import require_POST, require_GET
import razorpay
import json

from django.contrib.auth import authenticate


from .models import (
    Subject, Unit, Note,
    OTP, UserProfile,
    Transaction, PurchasedNote
)
from .utils import generate_otp, get_device_id, send_otp_sms


# ================= HOME =================
def home(request):
    return render(request, "hub/home.html")


# ================= SUBJECT FLOW =================
def subject_list(request):
    subjects = Subject.objects.all()
    return render(request, "hub/subjects.html", {"subjects": subjects})


def unit_list(request, subject_id):
    subject = get_object_or_404(Subject, id=subject_id)
    units = Unit.objects.filter(subject=subject)
    return render(request, "hub/units.html", {"subject": subject, "units": units})


# ================= NOTES =================
def note_list(request, unit_id):
    unit = get_object_or_404(Unit, pk=unit_id)
    notes = Note.objects.filter(unit=unit, is_active=True)

    purchased_notes = []

    if request.user.is_authenticated:
        purchased_notes = list(
            PurchasedNote.objects.filter(user=request.user)
            .values_list("note_id", flat=True)
        )

    return render(request, "hub/notes.html", {
        "unit": unit,
        "notes": notes,
        "purchased_notes": purchased_notes
    })



# ================= SEND OTP =================
# ================= SEND OTP =================
def send_otp(request):
    print("🔥 SEND OTP VIEW HIT")
    print("METHOD:", request.method)

    if request.method == "POST":
        mobile = request.POST.get("mobile")
        print("📱 Mobile received:", mobile)

        if not mobile or len(mobile) != 10:
            return render(request, "hub/send_otp.html", {
                "error": "Enter valid 10 digit mobile number"
            })

        # 🔁 Delete old OTPs (IMPORTANT)
        OTP.objects.filter(mobile=mobile).delete()

        otp = generate_otp()
        OTP.objects.create(mobile=mobile, otp=otp)

        print("✅ OTP GENERATED:", otp)

        try:
            send_otp_sms(mobile, otp)
            print("📩 OTP SMS FUNCTION CALLED")
        except Exception as e:
            print("❌ SMS ERROR:", e)

        return redirect(f"/verify-otp/?mobile={mobile}")

    return render(request, "hub/send_otp.html")





# ================= VERIFY OTP =================
def verify_otp(request):
    mobile = request.GET.get("mobile")

    if not mobile:
        return redirect("send_otp")

    if request.method == "POST":
        otp = request.POST.get("otp")

        otp_obj = OTP.objects.filter(mobile=mobile, otp=otp).first()

        if not otp_obj:
            return render(request, "hub/verify_otp.html", {
                "error": "Invalid OTP",
                "mobile": mobile
            })

        # ⏰ OTP expiry check (5 min)
        if otp_obj.is_expired():
            otp_obj.delete()
            return render(request, "hub/verify_otp.html", {
                "error": "OTP expired. Please try again.",
                "mobile": mobile
            })

        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        if not password or password != confirm_password:
            return render(request, "hub/verify_otp.html", {
                "error": "Passwords do not match",
                "mobile": mobile
            })

        # ✅ Create user
        user = User.objects.create_user(
            username=mobile,
            password=password
        )
        user.first_name = request.POST.get("name")
        user.email = request.POST.get("email")
        user.save()

        # 📱 Device lock
        device_id = get_device_id(request)

        UserProfile.objects.create(
            user=user,
            mobile=mobile,
            college_name=request.POST.get("college"),
            branch=request.POST.get("branch"),
            device_id=device_id
        )

        # 🧹 OTP single-use
        otp_obj.delete()

        login(request, user)
        return redirect("home")

    return render(request, "hub/verify_otp.html", {
        "mobile": mobile
    })


       

# ================= PAYMENT =================
@login_required
def create_order(request, note_id):
    note = get_object_or_404(Note, id=note_id)

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    amount = int(note.price * 100)

    order = client.order.create({
        "amount": amount,
        "currency": "INR",
        "payment_capture": 1
    })

    Transaction.objects.create(
        user=request.user,
        note=note,
        amount=note.price,
        order_id=order["id"],
        status="created"
    )

    return JsonResponse({
        "order_id": order["id"],
        "amount": amount,
        "key": settings.RAZORPAY_KEY_ID,
        "note_id": note.id,
        "note_title": note.title
    })


@login_required
def verify_payment(request):
    data = json.loads(request.body)

    order_id = data.get("razorpay_order_id")
    payment_id = data.get("razorpay_payment_id")
    signature = data.get("razorpay_signature")

    txn = get_object_or_404(Transaction, order_id=order_id)

    if txn.status == "success":
        return JsonResponse({"status": "already_processed"})

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature
        })
    except razorpay.errors.SignatureVerificationError:
        txn.status = "failed"
        txn.save()
        return JsonResponse({"status": "failed"})

    txn.payment_id = payment_id
    txn.status = "success"
    txn.save()

    PurchasedNote.objects.get_or_create(
        user=txn.user,
        note=txn.note
    )

    return JsonResponse({"status": "success"})


# ================= VIEW NOTE =================
@login_required
def view_note(request, note_id):
    note = get_object_or_404(Note, id=note_id)

    # ✅ FREE NOTE → allow everyone
    if note.price == 0:
        return render(request, "hub/view_note.html", {"note": note})

    # ❌ PAID NOTE → login required
    if not request.user.is_authenticated:
        return redirect("login")

    # ❌ PAID but not purchased
    if not PurchasedNote.objects.filter(user=request.user, note=note).exists():
        return HttpResponseForbidden("Access denied")

    # ✅ PAID + purchased
    return render(request, "hub/view_note.html", {"note": note})



# ================= PROFILE =================
@login_required
def profile(request):
    return render(request, "hub/profile.html", {
        "profile": request.user.userprofile
    })


@login_required
def edit_profile(request):
    profile = request.user.userprofile

    if request.method == "POST":
        request.user.first_name = request.POST.get("name")
        request.user.email = request.POST.get("email")
        profile.college_name = request.POST.get("college")
        profile.branch = request.POST.get("branch")

        request.user.save()
        profile.save()
        return redirect("profile")

    return render(request, "hub/edit_profile.html", {"profile": profile})


# ================= MY NOTES =================
@login_required
def my_notes(request):
    purchased = PurchasedNote.objects.filter(
        user=request.user
    ).select_related("note", "note__unit")

    return render(request, "hub/my_notes.html", {
        "purchased_notes": purchased
    })


# ================= COIN UNLOCK =================
@login_required
def unlock_with_coins(request, note_id):
    note = get_object_or_404(Note, id=note_id)
    profile = request.user.userprofile

    if PurchasedNote.objects.filter(user=request.user, note=note).exists():
        return JsonResponse({"status": "already_unlocked"})

    if profile.coins < note.coin_price:
        return JsonResponse({"status": "insufficient_coins"})

    profile.coins -= note.coin_price
    profile.save()

    PurchasedNote.objects.create(
        user=request.user,
        note=note
    )

    return JsonResponse({"status": "success"})


# ================= CHECK MOBILE =================
@require_GET
def check_mobile(request):
    mobile = request.GET.get("mobile")
    exists = User.objects.filter(username=mobile).exists()
    return JsonResponse({"exists": exists})


# ================= LOGOUT =================
@require_POST
def logout_view(request):
    logout(request)
    request.session.flush()
    return redirect("home")

def all_notes(request):
    notes = Note.objects.filter(is_active=True)

    purchased_notes = []
    if request.user.is_authenticated:
        purchased_notes = list(
            PurchasedNote.objects.filter(user=request.user)
            .values_list("note_id", flat=True)
        )

    return render(request, "hub/notes.html", {
        "notes": notes,
        "unit": None,
        "purchased_notes": purchased_notes
    })

def login_view(request):
    if request.method == "POST":
        mobile = request.POST.get("mobile")
        password = request.POST.get("password")

        user = authenticate(username=mobile, password=password)

        if user:
            login(request, user)
            return redirect("home")

        return render(request, "hub/login.html", {
            "error": "Invalid mobile number or password"
        })

    return render(request, "hub/login.html")


def forgot_password(request):
    print("🔥 forgot_password view hit")
    print("METHOD:", request.method)

    if request.method == "POST":
        mobile = request.POST.get("mobile")
        print("📱 Mobile received:", mobile)

        user = User.objects.filter(username=mobile).first()
        if not user:
            print("❌ User not found")
            return render(request, "hub/forgot_password.html", {
                "error": "Mobile number not registered"
            })

        OTP.objects.filter(mobile=mobile).delete()

        otp = generate_otp()
        print("✅ OTP GENERATED:", otp)

        OTP.objects.create(mobile=mobile, otp=otp)

        send_otp_sms(mobile, otp)
        print("📩 OTP SMS FUNCTION CALLED")

        return redirect(f"/reset-password/?mobile={mobile}")

    return render(request, "hub/forgot_password.html")

def reset_password(request):
    mobile = request.GET.get("mobile")

    if not mobile:
        return redirect("forgot_password")

    if request.method == "POST":
        otp = request.POST.get("otp")
        password = request.POST.get("password")
        confirm = request.POST.get("confirm_password")

        otp_obj = OTP.objects.filter(mobile=mobile, otp=otp).first()
        if not otp_obj:
            return render(request, "hub/reset_password.html", {
                "error": "Invalid OTP",
                "mobile": mobile
            })

        if otp_obj.is_expired():
            otp_obj.delete()
            return render(request, "hub/reset_password.html", {
                "error": "OTP expired",
                "mobile": mobile
            })

        if password != confirm:
            return render(request, "hub/reset_password.html", {
                "error": "Passwords do not match",
                "mobile": mobile
            })

        user = User.objects.get(username=mobile)
        user.set_password(password)
        user.save()

        otp_obj.delete()

        return redirect("login")

    return render(request, "hub/reset_password.html", {
        "mobile": mobile
    })
# ================= STATIC PAGES =================

def about(request):
    return render(request, "hub/about.html")

def help_page(request):
    return render(request, "hub/help.html")

def contact(request):
    return render(request, "hub/contact.html")

def terms(request):
    return render(request, "hub/terms.html")

def privacy(request):
    return render(request, "hub/privacy.html")
