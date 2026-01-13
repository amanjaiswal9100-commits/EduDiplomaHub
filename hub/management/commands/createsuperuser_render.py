from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = "Create superuser manually on Render Free plan"

    def handle(self, *args, **kwargs):
        username = "superadmin"
        email = "edudiplomahub@gmail.com"
        password = "Admin@123"

        if not User.objects.filter(username=username).exists():
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(self.style.SUCCESS("Superuser created"))
        else:
            self.stdout.write("Superuser already exists")
