#!/usr/bin/env bash
# Exit on error
set -o errexit

echo "==> Installing Python dependencies..."
pip install --upgrade pip
pip install -r backend/requirements.txt

echo "==> Collecting static files..."
python backend/manage.py collectstatic --noinput

echo "==> Applying database migrations..."
python backend/manage.py migrate --noinput

echo "==> Build finished successfully!"


echo "==> Ensuring admin superuser exists..."
python backend/manage.py shell -c "
import os
from django.contrib.auth import get_user_model
User = get_user_model()
username = os.environ.get('DJANGO_ADMIN_USERNAME')
password = os.environ.get('DJANGO_ADMIN_PASSWORD')
email = os.environ.get('DJANGO_ADMIN_EMAIL', '')
if username and password:
    u, created = User.objects.get_or_create(username=username, defaults={'email': email, 'is_staff': True, 'is_superuser': True})
    u.set_password(password)
    u.is_staff = True
    u.is_superuser = True
    u.save()
"