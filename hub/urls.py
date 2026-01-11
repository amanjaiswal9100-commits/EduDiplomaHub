from django.urls import path
from . import views

urlpatterns = [

    # HOME
    path("", views.home, name="home"),

    # AUTH
    path("login/", views.login_view, name="login"),
    path("signup/", views.send_otp, name="signup"),
    path("verify-otp/", views.verify_otp, name="verify_otp"),
    path("logout/", views.logout_view, name="logout"),

    # SUBJECT FLOW
    path("subjects/", views.subject_list, name="subject_list"),
    path("subjects/<int:subject_id>/units/", views.unit_list, name="unit_list"),

    # NOTES
    path("units/<int:unit_id>/notes/", views.note_list, name="note_list"),
    path("notes/", views.all_notes, name="all_notes"),
    path("note/<int:note_id>/view/", views.view_note, name="view_note"),

    # USER
    path("profile/", views.profile, name="profile"),
    path("profile/edit/", views.edit_profile, name="edit_profile"),
    path("my-notes/", views.my_notes, name="my_notes"),
    path("forgot-password/", views.forgot_password, name="forgot_password"),
    path("reset-password/", views.reset_password, name="reset_password"),


    # PAYMENT / API
    path("pay/<int:note_id>/", views.create_order, name="create_order"),
    path("verify-payment/", views.verify_payment, name="verify_payment"),
    path("unlock-coin/<int:note_id>/", views.unlock_with_coins, name="unlock_with_coins"),
    path("check-mobile/", views.check_mobile, name="check_mobile"),

    path("about/", views.about, name="about"),
path("help/", views.help_page, name="help"),
path("contact/", views.contact, name="contact"),
path("terms/", views.terms, name="terms"),
path("privacy/", views.privacy, name="privacy"),

]
