edu_erp/
├── config/                     # Django project settings
│   ├── __init__.py
│   ├── settings.py             # Use env variables for secrets
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
├── apps/
│   ├── core/                   # Custom user model, base models, utilities
│   ├── organization/           # Multi-tenant school model
│   ├── authentication/         # Custom auth with AllAuth
│   ├── students/               # Student management
│   ├── student_portal/               # Student management
│   ├── teachers/               # Teacher management
│   ├── academics/              # Classes, subjects, timetable
│   ├── attendance/             # Attendance tracking
│   ├── examination/            # Exams, results, report cards
│   ├── finance/                # Fees, payments, accounting
│   ├── library/                # Book management
│   ├── inventory/              # Inventory management
│   ├── transportation/         # Transport management
│   ├── hr/                     # HR, payroll, staff management
│   ├── communications/         # Notifications, announcements
│   ├── reports/                # Reports, analytics, dashboard
│   └── payments/               # Payment gateway integration
│
├── static/                     # Static files (CSS, JS, Images)
├── templates/                  # HTML templates
├── templatestags/              # templatestags
├── scripts/                    # Deployement Scripts
├── media/                      # Media Files
├── utis/                       # Utilities of Projects
│
├── docker/                     # Docker-related files
├── Dockerfile              # Build Django app
├── docker-compose.yml      # Compose for Django + DB + Redis
├── entrypoint.sh           # Entrypoint script for container
│   
│
├── docs/                       # Documentation
│   ├── INSTALLATION.md
│   ├── LOADDATA.md
│   ├── README.md
│   ├── USER_GUIDE.md
│   ├── DEVELOPER_GUIDE.md
│   ├── DEPLOYEMENT_GUIDE.md
│   ├── DEPLOYEMENT.md
│   ├── DELETE_MIGRATIONS.md
│   ├── API_REFERENCE.md
│   ├── TESTING.md
│   ├── SECURITY.md
│   ├── FAQ.md
│   └── STRUCTURE.md
│
├── .env.example                # Environment variables sample
├── .gitignore                  # Ignore unnecessary files
├── LICENSE                     # Open-source license
├── README.md                   # Project overview
├── requirements.txt            # Python dependencies
├── db.sqlite3                  # Python dependencies
└── manage.py                   # Django manage script