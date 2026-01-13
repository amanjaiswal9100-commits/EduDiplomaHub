from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = "Create superuser for Render deployment"

    def handle(self, *args, **options):
        username = "admin"
        email = "edudiplomahub@gmail.com"
        password = "Admin@123"

        if User.objects.filter(username=username).exists():
            self.stdout.write("Admin already exists")
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )
        self.stdout.write("Superuser created successfully")
