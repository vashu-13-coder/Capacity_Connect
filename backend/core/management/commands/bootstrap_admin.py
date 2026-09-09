import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create or reset a Django admin user from environment variables."

    def handle(self, *args, **options):
        username = os.getenv("DJANGO_ADMIN_USERNAME", "admin").strip()
        email = os.getenv("DJANGO_ADMIN_EMAIL", "").strip()
        password = os.getenv("DJANGO_ADMIN_PASSWORD", "")

        if not username:
            raise CommandError("DJANGO_ADMIN_USERNAME cannot be empty.")
        if not password:
            raise CommandError(
                "DJANGO_ADMIN_PASSWORD is required and must be set in the environment."
            )

        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email},
        )

        if email:
            user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save()

        action = "Created" if created else "Reset"
        self.stdout.write(
            self.style.SUCCESS(f"{action} Django admin user '{username}' successfully.")
        )
