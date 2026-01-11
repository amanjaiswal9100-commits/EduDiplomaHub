from django.contrib import admin
from .models import (
    Subject, Unit, Note,
    UserProfile,
    PurchasedNote,
    Transaction
)

# ==================================================
# SUBJECT / UNIT
# ==================================================
@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("unit_name", "subject")
    list_filter = ("subject",)
    search_fields = ("unit_name", "subject__name")


# ==================================================
# NOTE ADMIN
# ==================================================
@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "unit",
        "price",
        "coin_price",
        "access_type",
        "is_active",
    )

    list_filter = ("unit", "is_active")
    search_fields = ("title", "unit__unit_name")

    list_editable = ("price", "coin_price", "is_active")

    def access_type(self, obj):
        if obj.price == 0 and obj.coin_price == 0:
            return "🆓 FREE"
        elif obj.price > 0 and obj.coin_price > 0:
            return "₹ + 🪙 BOTH"
        elif obj.price > 0:
            return "₹ PAID"
        else:
            return "🪙 COINS"

    access_type.short_description = "Access Type"


# ==================================================
# USER PROFILE ADMIN
# ==================================================
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):

    list_display = (
        "mobile",
        "user_name",
        "college_name",
        "branch",
        "coins",
        "referral_code",
        "referred_by_user",
        "created_at",
    )

    search_fields = (
        "mobile",
        "user__first_name",
        "user__email",
        "college_name",
        "branch",
    )

    list_filter = ("college_name", "branch", "created_at")
    ordering = ("-created_at",)

    fields = (
        "user",
        "mobile",
        "college_name",
        "branch",
        "coins",
        "referral_code",
        "referred_by",
        "created_at",
    )

    readonly_fields = (
        "referral_code",
        "referred_by",
        "created_at",
    )

    actions = ["add_50_coins", "add_100_coins", "reset_coins"]

    def user_name(self, obj):
        return obj.user.first_name or "—"
    user_name.short_description = "Name"

    def referred_by_user(self, obj):
        return obj.referred_by.first_name if obj.referred_by else "—"
    referred_by_user.short_description = "Referred By"

    # ===== ADMIN ACTIONS =====
    def add_50_coins(self, request, queryset):
        for profile in queryset:
            profile.coins += 50
            profile.save()
    add_50_coins.short_description = "➕ Add 50 coins"

    def add_100_coins(self, request, queryset):
        for profile in queryset:
            profile.coins += 100
            profile.save()
    add_100_coins.short_description = "➕ Add 100 coins"

    def reset_coins(self, request, queryset):
        queryset.update(coins=0)
    reset_coins.short_description = "♻ Reset coins to 0"


# ==================================================
# PURCHASED NOTES
# ==================================================
@admin.register(PurchasedNote)
class PurchasedNoteAdmin(admin.ModelAdmin):
    list_display = ("user", "note", "purchased_at")
    search_fields = ("user__username", "note__title")
    list_filter = ("purchased_at",)
    ordering = ("-purchased_at",)


# ==================================================
# TRANSACTIONS
# ==================================================
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "note",
        "amount",
        "status",
        "created_at",
    )

    list_filter = ("status", "created_at")
    search_fields = ("user__username", "note__title")
    ordering = ("-created_at",)
