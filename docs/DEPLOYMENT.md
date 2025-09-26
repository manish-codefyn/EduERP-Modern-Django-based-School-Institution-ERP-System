
## 🚀 docs/DEPLOYMENT.md

```markdown
# 🚀 Deployment Guide

## Production Deployment Overview

EduERP supports multiple deployment strategies:
- **Traditional VPS/Server deployment**
- **Docker-based deployment**
- **Cloud platform deployment** (AWS, GCP, Azure)
- **Kubernetes deployment**

## 🏗️ Traditional Server Deployment

### Prerequisites
- Ubuntu 20.04 LTS / CentOS 8+
- Nginx
- PostgreSQL
- Redis
- Python 3.10+

### Step 1: Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install python3-pip python3-venv nginx postgresql postgresql-contrib redis-server


Step 2: Database Configuration

# Create PostgreSQL user and database
sudo -u postgres psql
CREATE DATABASE eduerp_prod;
CREATE USER eduerp_prod_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE eduerp_prod TO eduerp_prod_user;

Step 3: Application Deployment

# Clone repository
git clone https://github.com/yourusername/EduERP.git /opt/eduerp
cd /opt/eduerp

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
nano .env  # Edit with production values

Step 4: Gunicorn Setup

[Unit]
Description=EduERP Gunicorn Daemon
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/eduerp
ExecStart=/opt/eduerp/venv/bin/gunicorn --access-logfile - --workers 3 --bind unix:/opt/eduerp/eduerp.sock config.wsgi:application

[Install]
WantedBy=multi-user.target

Step 5: Nginx Configuration
server {
    listen 80;
    server_name yourdomain.com;

    location /static/ {
        alias /opt/eduerp/static/;
    }

    location /media/ {
        alias /opt/eduerp/media/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/opt/eduerp/eduerp.sock;
    }
}
Step 6: Final Steps

# Enable site
sudo ln -s /etc/nginx/sites-available/eduerp /etc/nginx/sites-enabled

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Start services
sudo systemctl daemon-reload
sudo systemctl start eduerp
sudo systemctl enable eduerp
sudo systemctl restart nginx

🐳 Docker Deployment
Using Docker Compose

# docker-compose.prod.yml
version: '3.8'

services:
  db:
    image: postgres:13
    environment:
      POSTGRES_DB: eduerp
      POSTGRES_USER: eduerp_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:6-alpine

  web:
    build: .
    command: gunicorn config.wsgi:application --bind 0.0.0.0:8000
    volumes:
      - static_volume:/app/static
      - media_volume:/app/media
    environment:
      - DEBUG=False
    depends_on:
      - db
      - redis

  nginx:
    image: nginx:1.21-alpine
    ports:
      - "80:80"
    volumes:
      - static_volume:/app/static
      - media_volume:/app/media
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - web

volumes:
  postgres_data:
  static_volume:
  media_volume:

  ☁️ Cloud Deployment

  AWS Elastic Beanstalk
Create requirements.txt for AWS

Django>=5.0,<5.1
gunicorn==20.1.0
psycopg2-binary==2.9.6
# ... other dependencies

Heroku Deployment

web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT

Deploy

heroku create your-eduerp-app
heroku addons:create heroku-postgresql:hobby-dev
heroku config:set DEBUG=False
git push heroku main

🔧 Multi-tenant Configuration

Domain-based Tenancy
Configure in config/settings/production.py:

MULTI_TENANT_CONFIG = {
    'PUBLIC_SCHEMA': 'public',
    'TENANT_MODEL': 'organization.School',
    'DOMAIN_MODEL': 'organization.Domain',
}

MIDDLEWARE = [
    # ... other middleware
    'django_tenants.middleware.main.TenantMainMiddleware',
]

Database Schema Setup

# Each school gets its own schema
python manage.py create_tenant \
    --schema-name=school1 \
    --name="School One" \
    --domain-domain=school1.yourdomain.com


🔒 Security Hardening

SSL Configuration

# Nginx SSL configuration
server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-XSS-Protection "1; mode=block";
    add_header X-Content-Type-Options "nosniff";
}

Django Security Settings    
# production.py
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

📊 Monitoring and Logging   
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/eduerp/django.log',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

🔄 Backup Strategy

Automated Backups

#!/bin/bash
# backup.sh
DATE=$(date +%Y-%m-%d_%H-%M-%S)
pg_dump -U eduerp_user eduerp_prod > /backups/eduerp_$DATE.sql
find /backups -name "*.sql" -mtime +7 -delete

Cron Job for Backups

0 2 * * * /opt/eduerp/scripts/backup.sh