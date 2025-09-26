# EduERP - Modern Django-based School & Institution ERP System 🎓

EduERP is a **robust, open-source School & Institution Management System** built with Django. It is designed to help schools, colleges, and educational institutions manage **students, teachers, academics, finance, HR, communication, and more**, all from a centralized platform.

---

![Django](https://img.shields.io/badge/Django-4.2-green) 
![Python](https://img.shields.io/badge/Python-3.11-blue) 
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13-blue) 
![License](https://img.shields.io/badge/License-MIT-yellow)

---
## 🌟 Features

### Student Features
- Personal dashboard with academic overview
- Course registration and management
- Grade tracking and transcript view
- Attendance monitoring
- Assignment submission portal
- Fee payment integration
- Communication with faculty

### Admin Features
- Complete student lifecycle management
- Course and curriculum management
- Attendance and grade management
- Financial management
- Reporting and analytics
- Multi-role user management

### Technical Features
- RESTful API architecture
- Real-time notifications
- File upload and management
- Responsive design
- Secure authentication
- Docker containerization

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 13+
- Redis (for caching)
- Docker (optional)

### Installation

#### Method 1: Traditional Setup
```bash
# Clone repository
https://github.com/manish-codefyn/EduERP-Modern-Django-based-School-Institution-ERP-System.git
cd EduERP-Modern-Django-based-School-Institution-ERP-System

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Environment setup
cp .env.example .env
# Edit .env with your configurations

# Database setup
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver# EduERP-Modern-Django-based-School-Institution-ERP-System
