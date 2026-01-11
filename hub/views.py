from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.http import JsonResponse, HttpResponseForbidden
from django.conf import settings
from django.views.decorators.http import require_POST, require_GET
from django.core.mail import send_mail
import razorpay
import json

from .models import (
    Subject, Unit, Note,
    OTP, UserProfile,
    Transaction, PurchasedNote
)
from .utils import generate_otp, get_device_id


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


# =========================================================
# ======================= SEND OTP (EMAIL) =================
# =========================================================
def send_otp(request):
    if request.method == "POST":
        email = request.POST.get("email")

        if not email:
            return render(request, "hub/send_otp.html", {
                "error": "Please enter email"
            })

        OTP.objects.filter(email=email).delete()

        otp = generate_otp()
        OTP.objects.create(email=email, otp=otp)

        send_mail(
            subject="EduDiplomaHub OTP Verification",
            message=f"Your OTP for EduDiplomaHub login is {otp}. Do not share it.",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
            fail_silently=False,
        )

        return redirect(f"/verify-otp/?email={email}")

    return render(request, "hub/send_otp.html")


# =========================================================
# ======================= VERIFY OTP ======================
# =========================================================
def verify_otp(request):
    email = request.GET.get("email")

    if not email:
        return redirect("signup")

    user_exists = User.objects.filter(email=email).exists()

    if request.method == "POST":
        otp = request.POST.get("otp")

        otp_obj = OTP.objects.filter(email=email, otp=otp).first()

        if not otp_obj:
            return render(request, "hub/verify_otp.html", {
                "error": "Invalid OTP",
                "email": email,
                "user_exists": user_exists
            })

        if otp_obj.is_expired():
            otp_obj.delete()
            return render(request, "hub/verify_otp.html", {
                "error": "OTP expired",
                "email": email,
                "user_exists": user_exists
            })

        # 🔁 EXISTING USER → DIRECT LOGIN
        if user_exists:
            user = User.objects.get(email=email)
            otp_obj.delete()
            login(request, user)
            return redirect("home")

        # 🆕 NEW USER → CREATE ACCOUNT
        password = request.POST.get("password")
        confirm = request.POST.get("confirm_password")

        if password != confirm:
            return render(request, "hub/verify_otp.html", {
                "error": "Passwords do not match",
                "email": email,
                "user_exists": False
            })

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password
        )
        user.first_name = request.POST.get("name")
        user.save()

        UserProfile.objects.create(
            user=user,
            mobile="",
            college_name=request.POST.get("college"),
            branch=request.POST.get("branch"),
        )

        otp_obj.delete()
        login(request, user)
        return redirect("home")

    return render(request, "hub/verify_otp.html", {
        "email": email,
        "user_exists": user_exists
    })



# ================= LOGIN =================
def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(username=email, password=password)

        if user:
            login(request, user)
            return redirect("home")

        return render(request, "hub/login.html", {
            "error": "Invalid email or password"
        })

    return render(request, "hub/login.html")


# ================= FORGOT PASSWORD =================
def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email")
        user = User.objects.filter(username=email).first()

        if not user:
            return render(request, "hub/forgot_password.html", {
                "error": "Email not registered"
            })

        OTP.objects.filter(email=email).delete()
        otp = generate_otp()
        OTP.objects.create(email=email, otp=otp)

        send_mail(
            subject="EduDiplomaHub Password Reset OTP",
            message=f"Your OTP for password reset is {otp}.",
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[email],
        )

        return redirect(f"/reset-password/?email={email}")

    return render(request, "hub/forgot_password.html")


# ================= RESET PASSWORD =================
def reset_password(request):
    email = request.GET.get("email")

    if request.method == "POST":
        otp = request.POST.get("otp")
        password = request.POST.get("password")
        confirm = request.POST.get("confirm_password")

        otp_obj = OTP.objects.filter(email=email, otp=otp).first()
        if not otp_obj or otp_obj.is_expired():
            return render(request, "hub/reset_password.html", {
                "error": "Invalid or expired OTP",
                "email": email
            })

        if password != confirm:
            return render(request, "hub/reset_password.html", {
                "error": "Passwords do not match",
                "email": email
            })

        user = User.objects.get(username=email)
        user.set_password(password)
        user.save()

        otp_obj.delete()
        return redirect("login")

    return render(request, "hub/reset_password.html", {"email": email})


# ================= LOGOUT =================
@require_POST
def logout_view(request):
    logout(request)
    request.session.flush()
    return redirect("home")


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

    client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    client.utility.verify_payment_signature({
        "razorpay_order_id": order_id,
        "razorpay_payment_id": payment_id,
        "razorpay_signature": signature
    })

    txn.payment_id = payment_id
    txn.status = "success"
    txn.save()

    PurchasedNote.objects.get_or_create(
        user=txn.user,
        note=txn.note
    )

    return JsonResponse({"status": "success"})


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
# ================= ALL NOTES (FIXED) =================
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
# ================= VIEW NOTE (RESTORED) =================
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

    # Already unlocked
    if PurchasedNote.objects.filter(user=request.user, note=note).exists():
        return JsonResponse({"status": "already_unlocked"})

    # Not enough coins
    if profile.coins < note.coin_price:
        return JsonResponse({"status": "insufficient_coins"})

    # Deduct coins
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
