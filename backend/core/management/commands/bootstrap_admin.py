import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from core.models import Role, UserProfile


class Command(BaseCommand):
    help = "Create or reset a Django admin user from environment variables."

    def handle(self, *args, **options):
        username = os.getenv("DJANGO_ADMIN_USERNAME", "Admin").strip()
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

        UserProfile.objects.update_or_create(
            user=user,
            defaults={"role": Role.ADMIN},
        )

        action = "Created" if created else "Updated"
        self.stdout.write(
            self.style.SUCCESS(
                f"{action} Django admin user '{username}' successfully."
            )
        )
