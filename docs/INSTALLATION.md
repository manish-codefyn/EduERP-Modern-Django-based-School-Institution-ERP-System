# 🔧 Installation Guide

## System Requirements

### Minimum Requirements
- **Python**: 3.10 or higher
- **PostgreSQL**: 12.0 or higher
- **Redis**: 6.0 or higher (for caching and queues)
- **Memory**: 4GB RAM minimum
- **Storage**: 10GB free space

### Recommended for Production
- **Python**: 3.11+
- **PostgreSQL**: 14+
- **Redis**: 7.0+
- **Memory**: 8GB RAM or more
- **Storage**: 50GB SSD

## 🏁 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/EduERP.git
cd EduERP


2. Create Virtual Environment

python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows

3. Install Dependencies

pip install -r requirements.txt

4. Environment Configuration
cp .env.example .env
# Edit .env file with your configuration

5. Database Setup
python manage.py migrate

6. Create Superuser
python manage.py createsuperuser

7. Collect Static Files
python manage.py collectstatic

8. Run Development Server
python manage.py runserver

Visit http://localhost:8000 to access the application.

📋 Detailed Installation

PostgreSQL Database Setup
Install PostgreSQL

# Ubuntu/Debian
sudo apt-get update
sudo apt-get install postgresql postgresql-contrib

# CentOS/RHEL
sudo yum install postgresql-server postgresql-contrib

Create Database and User
CREATE DATABASE eduerp;
CREATE USER eduerp_user WITH PASSWORD 'your_secure_password';
ALTER ROLE eduerp_user SET client_encoding TO 'utf8';
ALTER ROLE eduerp_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE eduerp_user SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE eduerp TO eduerp_user;

Environment Variables Configuration 
Edit the .env file:
# Django Settings
DEBUG=False
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1,yourdomain.com

# Database
DB_NAME=eduerp
DB_USER=eduerp_user
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Payment Gateway (Optional)
RAZORPAY_KEY_ID=your_razorpay_key
RAZORPAY_KEY_SECRET=your_razorpay_secret


Docker Installation (Alternative)
# Follow official Docker installation guide for your OS
Run with Docker Compose
docker-compose up -d

Run Migrations
docker-compose exec web python manage.py migrate

Create Superuser

docker-compose exec web python manage.py createsuperuser


🧪 Verification Steps
After installation, verify everything is working:

Check Django Admin

Visit http://localhost:8000/admin

Login with superuser credentials

Test Database Connection
python manage.py check --database default

Run Basic Tests

python manage.py test apps.core.tests

❗ Troubleshooting
Common Issues
Database Connection Error

Verify PostgreSQL is running

Check database credentials in .env

Ensure database exists

Port Already in Use

# Find process using port 8000
lsof -i :8000
# Kill the process or use different port
python manage.py runserver 8001

Permission Errors
# Fix file permissions
chmod -R 755 static/
chmod -R 755 media/

Getting Help
If you encounter issues:

Check the FAQ

Search existing [GitHub Issues]

Create a new issue with detailed error information

