from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):
    help = "Create clean superadmin for Render"

    def handle(self, *args, **options):
        username = "superadmin"
        email = "edudiplomahub@gmail.com"
        password = "Admin@123"

        if User.objects.filter(username=username).exists():
            self.stdout.write("superadmin already exists")
            return

        User.objects.create_superuser(
            username=username,
            email=email,
            password=password
        )

        self.stdout.write("superadmin created successfully")
