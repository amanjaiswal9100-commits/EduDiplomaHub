from django.apps import AppConfig
from django.db.models.signals import post_migrate


def create_admin(sender, **kwargs):
    from django.contrib.auth.models import User

    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser(
            username="admin",
            email="edudiplomahub@gmail.com",
            password="Admin@123"
        )


class HubConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'hub'

    def ready(self):
        post_migrate.connect(create_admin, sender=self)
