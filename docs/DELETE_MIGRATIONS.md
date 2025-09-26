
 For Delete Migrations and Db

1. find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
2. find . -path "*/migrations/*.pyc" -delete
3. rm db.sqlite3
4. pip uninstall django
5. pip install django
6. python manage.py makemigrations
7. python manage.py migrate
8. python manage.py createsuperuser
8. # Load all academic data
python manage.py load_academic_data

9. python manage.py runserver

