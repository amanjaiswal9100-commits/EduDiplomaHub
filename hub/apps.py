from django.apps import AppConfig
from django.db.models.signals import post_migrate

def create_admin(sender, **kwargs):
    from django.contrib.auth.models import User

    admin, created = User.objects.get_or_create(
        username="admin",
        defaults={
            "email": "edudiplomahub@gmail.com",
            "is_staff": True,
            "is_superuser": True,
        }
    )

    # 🔑 FORCE PASSWORD SET (SAFE HERE)
    admin.set_password("Admin@123")
    admin.save()

class HubConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hub'

    def ready(self):
        post_migrate.connect(create_admin, sender=self)
