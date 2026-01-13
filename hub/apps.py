from django.apps import AppConfig

class HubConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hub'

    def ready(self):
        from django.contrib.auth.models import User

        # 🔥 DELETE ALL EXISTING ADMINS
        User.objects.filter(is_superuser=True).delete()

        # 🔥 CREATE FRESH SUPERUSER
        User.objects.create_superuser(
            username="admin",
            email="edudiplomahub@gmail.com",
            password="Admin@123"
        )
