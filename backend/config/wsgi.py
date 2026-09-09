"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named `application`.
"""

import os

from django.core.management import call_command
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()

# Disabled by default. When explicitly enabled through Render environment
# variables, reset/create the admin without storing credentials in Git.
if os.getenv('DJANGO_ADMIN_BOOTSTRAP', '').lower() in ('true', '1', 'yes'):
    call_command('bootstrap_admin')
