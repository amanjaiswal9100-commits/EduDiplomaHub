from django.apps import AppConfig


class HubConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hub'


def ready(self):
    from django.contrib.auth.models import User

    try:
        admin_user, created = User.objects.get_or_create(
            username="admin",
            defaults={
                "email": "edudiplomahub@gmail.com",
                "is_staff": True,
                "is_superuser": True,
            }
        )

        # 🔥 FORCE RESET PASSWORD (IMPORTANT)
        admin_user.set_password("jaisu@1234")
        admin_user.save()

    except Exception as e:
        print("Admin auto-setup error:", e)

