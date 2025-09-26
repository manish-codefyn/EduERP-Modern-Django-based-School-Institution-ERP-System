
# Load all academic data
python manage.py load_academic_data

# Load specific model only
python manage.py load_academic_data --model academicyear
python manage.py load_academic_data --model class

# Or use individual commands
python manage.py load_academic_years
python manage.py load_classes
python manage.py load_sections
python manage.py load_houses
python manage.py load_subjects
python manage.py load_timetables


python manage.py load_academic_data --model institution
python manage.py load_academic_data --model department
python manage.py load_academic_data --model teacher
python manage.py load_academic_data --model academicyear
python manage.py load_academic_data --model class
python manage.py load_academic_data --model section
python manage.py load_academic_data --model house
python manage.py load_academic_data --model subject
python manage.py load_academic_data --model timetable

python manage.py load_fee_structures --institution="Main Campus"