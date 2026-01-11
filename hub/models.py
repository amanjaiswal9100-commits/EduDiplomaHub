from django.db import models
from django.contrib.auth.models import User
import uuid
from datetime import timedelta
from django.utils import timezone


# ================= SUBJECT =================
class Subject(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


# ================= UNIT =================
class Unit(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    unit_name = models.CharField(max_length=100)
    unit_description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.subject.name} - {self.unit_name}"


# ================= NOTE =================
class Note(models.Model):
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to="notes/")
    price = models.PositiveIntegerField(default=0)
    coin_price = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def is_free(self):
        return self.price == 0 and self.coin_price == 0

    def __str__(self):
        return self.title


# ================= USER PROFILE =================
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    mobile = models.CharField(max_length=15, unique=True)

    college_name = models.CharField(max_length=200, blank=True)
    branch = models.CharField(max_length=100, blank=True)

    referral_code = models.CharField(max_length=20, unique=True)
    referred_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="referrals"
    )

    coins = models.PositiveIntegerField(default=0)
    device_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = "EDH" + uuid.uuid4().hex[:6].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.mobile


# ================= OTP =================
class OTP(models.Model):
    mobile = models.CharField(max_length=15)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=5)


# ================= PURCHASE =================
class PurchasedNote(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    note = models.ForeignKey(Note, on_delete=models.CASCADE)
    purchased_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "note")


# ================= TRANSACTION =================
class Transaction(models.Model):
    STATUS = (
        ("created", "Created"),
        ("success", "Success"),
        ("failed", "Failed"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    note = models.ForeignKey(Note, on_delete=models.CASCADE)
    amount = models.IntegerField()
    order_id = models.CharField(max_length=100, unique=True)
    payment_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS)
    created_at = models.DateTimeField(auto_now_add=True)
