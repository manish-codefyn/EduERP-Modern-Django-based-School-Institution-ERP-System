#!/bin/bash

# Deployment script for School Management System

set -e

echo "Starting deployment..."

# Pull latest changes
git pull origin main

# Create/update environment file
cp .env.example .env
# Edit .env with actual values before running

# Build and start containers
docker-compose down
docker-compose up --build -d

# Run migrations
docker-compose exec web python manage.py migrate --noinput

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Create superuser if not exists
docker-compose exec web python manage.py createsuperuser --noinput || true

echo "Deployment completed successfully!"



