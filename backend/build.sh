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
