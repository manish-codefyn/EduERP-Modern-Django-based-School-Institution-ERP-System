import json
import os
import uuid
from django.core.management.base import BaseCommand
from apps.academics.models import AcademicYear, Class, Section, House, Subject, Timetable
from apps.organization.models import Institution, Department
from apps.teachers.models import Teacher

class Command(BaseCommand):
    help = 'Load academic data from JSON files'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--model',
            type=str,
            help='Specific model to load (institution, academicyear, class, section, house, subject, timetable)'
        )
    
    def handle(self, *args, **options):
        model_name = options.get('model')
        
        # Load institutions first as they are required for other models
        if not model_name or model_name == 'institution':
            self.load_institutions()
        if not model_name or model_name == 'department':
            self.load_departments()
            
        if not model_name or model_name == 'teacher':
            self.load_teachers()
                        
        if not model_name or model_name == 'academicyear':
            self.load_academic_years()
        if not model_name or model_name == 'class':
            self.load_classes()
        if not model_name or model_name == 'section':
            self.load_sections()
        if not model_name or model_name == 'house':
            self.load_houses()
        if not model_name or model_name == 'subject':
            self.load_subjects()
        if not model_name or model_name == 'timetable':
            self.load_timetables()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully loaded academic data')
        )
    
    def load_institutions(self):
        """Load institutions from JSON file"""
        file_path = os.path.join('apps', 'academics', 'data', 'institutions.json')
        
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                
            for item in data:
                try:
                    Institution.objects.update_or_create(
                        code=item['code'],
                        defaults={
                            'name': item['name'],
                            'slug': item.get('slug', item['code']),
                            'short_name': item.get('short_name'),
                            'type': item.get('type', 'school'),
                            'address': item.get('address', ''),
                            'city': item.get('city'),
                            'state': item.get('state'),
                            'country': item.get('country', 'India'),
                            'pincode': item.get('pincode'),
                            'website': item.get('website'),
                            'contact_email': item.get('contact_email'),
                            'contact_phone': item.get('contact_phone'),
                            'alternate_phone': item.get('alternate_phone'),
                            'primary_color': item.get('primary_color', '#0D47A1'),
                            'secondary_color': item.get('secondary_color', '#1976D2'),
                            'accent_color': item.get('accent_color', '#42A5F5'),
                            'text_dark_color': item.get('text_dark_color', '#212121'),
                            'text_light_color': item.get('text_light_color', '#FFFFFF'),
                            'text_muted_color': item.get('text_muted_color', '#757575'),
                            'academic_year_start': item.get('academic_year_start'),
                            'academic_year_end': item.get('academic_year_end'),
                            'timezone': item.get('timezone', 'UTC'),
                            'fiscal_year_start': item.get('fiscal_year_start'),
                            'language': item.get('language', 'English'),
                            'currency': item.get('currency', 'INR'),
                            'is_active': item.get('is_active', True),
                            'established_date': item.get('established_date')
                        }
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'Successfully loaded institution: {item["name"]}')
                    )
                    
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error loading institution {item["name"]}: {str(e)}')
                    )
                    
        except FileNotFoundError:
            self.stdout.write(
                self.style.WARNING('Institutions JSON file not found')
            )
    def load_departments(self):
        """Load departments from JSON file"""
        file_path = os.path.join('apps', 'academics', 'data', 'departments.json')
        
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                
            for item in data:
                try:
                    institution = Institution.objects.get(code=item['institution_code'])
                    
                    Department.objects.update_or_create(
                        institution=institution,
                        code=item['code'],
                        defaults={
                            'name': item['name'],
                            'short_name': item.get('short_name'),
                            'department_type': item.get('department_type', 'academic'),
                            'description': item.get('description', ''),
                            'email': item.get('email'),
                            'phone': item.get('phone'),
                            'office_location': item.get('office_location'),
                            'is_active': item.get('is_active', True),
                            'established_date': item.get('established_date')
                        }
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'Successfully loaded department: {item["name"]}')
                    )
                    
                except Institution.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'Institution {item["institution_code"]} not found for department {item["name"]}')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error loading department {item["name"]}: {str(e)}')
                    )
                    
        except FileNotFoundError:
            self.stdout.write(
                self.style.WARNING('Departments JSON file not found')
            )
            
            
    def load_teachers(self):
        """Load teachers from JSON file"""
        file_path = os.path.join('apps', 'academics', 'data', 'teachers.json')
        
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                
            for item in data:
                try:
                    institution = Institution.objects.get(code=item['institution_code'])
                    
                    Teacher.objects.update_or_create(
                        employee_id=item['employee_id'],
                        defaults={
                            'institution': institution,
                            'first_name': item['first_name'],
                            'last_name': item['last_name'],
                            'email': item.get('email'),
                            'mobile': item.get('mobile'),
                            'gender': item.get('gender'),
                            'dob': item.get('dob'),
                            'qualification': item.get('qualification'),
                            'experience': item.get('experience', 0),
                            'specialization': item.get('specialization'),
                            'joining_date': item.get('joining_date'),
                            'is_active': item.get('is_active', True)
                        }
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'Successfully loaded teacher: {item["first_name"]} {item["last_name"]}')
                    )
                    
                except Institution.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'Institution {item["institution_code"]} not found for teacher {item["first_name"]} {item["last_name"]}')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error loading teacher {item["first_name"]} {item["last_name"]}: {str(e)}')
                    )
                    
        except FileNotFoundError:
            self.stdout.write(
                self.style.WARNING('Teachers JSON file not found')
            )
                
    def load_academic_years(self):
        file_path = os.path.join('apps', 'academics', 'data', 'academic_years.json')
        
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                
            for item in data:
                try:
                    institution = Institution.objects.get(code=item['institution_code'])
                    
                    AcademicYear.objects.update_or_create(
                        institution=institution,
                        name=item['name'],
                        defaults={
                            'start_date': item['start_date'],
                            'end_date': item['end_date'],
                            'is_current': item.get('is_current', False)
                        }
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'Successfully loaded academic year: {item["name"]}')
                    )
                    
                except Institution.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'Institution {item["institution_code"]} not found for academic year {item["name"]}')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error loading academic year {item["name"]}: {str(e)}')
                    )
                    
        except FileNotFoundError:
            self.stdout.write(
                self.style.WARNING('Academic years JSON file not found')
            )
    
    def load_classes(self):
        file_path = os.path.join('apps', 'academics', 'data', 'classes.json')
        
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                
            for item in data:
                try:
                    institution = Institution.objects.get(code=item['institution_code'])
                    
                    Class.objects.update_or_create(
                        institution=institution,
                        code=item['code'],
                        defaults={
                            'name': item['name'],
                            'capacity': item.get('capacity', 40),
                            'room_number': item.get('room_number', ''),
                            'is_active': item.get('is_active', True)
                        }
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'Successfully loaded class: {item["name"]}')
                    )
                    
                except Institution.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'Institution {item["institution_code"]} not found for class {item["name"]}')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error loading class {item["name"]}: {str(e)}')
                    )
                    
        except FileNotFoundError:
            self.stdout.write(
                self.style.WARNING('Classes JSON file not found')
            )
    
    def load_sections(self):
        file_path = os.path.join('apps', 'academics', 'data', 'sections.json')
        
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                
            for item in data:
                try:
                    institution = Institution.objects.get(code=item['institution_code'])
                    class_obj = Class.objects.get(institution=institution, code=item['class_code'])
                    
                    Section.objects.update_or_create(
                        institution=institution,
                        class_name=class_obj,
                        name=item['name'],
                        defaults={
                            'capacity': item.get('capacity', 40),
                            'is_active': item.get('is_active', True)
                        }
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'Successfully loaded section: {class_obj.name} - {item["name"]}')
                    )
                    
                except (Institution.DoesNotExist, Class.DoesNotExist) as e:
                    self.stdout.write(
                        self.style.WARNING(f'Related object not found for section {item["name"]}: {str(e)}')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error loading section {item["name"]}: {str(e)}')
                    )
                    
        except FileNotFoundError:
            self.stdout.write(
                self.style.WARNING('Sections JSON file not found')
            )
    
    def load_houses(self):
        file_path = os.path.join('apps', 'academics', 'data', 'houses.json')
        
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                
            for item in data:
                try:
                    institution = Institution.objects.get(code=item['institution_code'])
                    
                    House.objects.update_or_create(
                        institution=institution,
                        name=item['name'],
                        defaults={
                            'color': item.get('color', ''),
                            'description': item.get('description', ''),
                            'is_active': item.get('is_active', True)
                        }
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'Successfully loaded house: {item["name"]}')
                    )
                    
                except Institution.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(f'Institution {item["institution_code"]} not found for house {item["name"]}')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error loading house {item["name"]}: {str(e)}')
                    )
                    
        except FileNotFoundError:
            self.stdout.write(
                self.style.WARNING('Houses JSON file not found')
            )
    
    def load_subjects(self):
        file_path = os.path.join('apps', 'academics', 'data', 'subjects.json')
        
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                
            for item in data:
                try:
                    institution = Institution.objects.get(code=item['institution_code'])
                    department = None
                    
                    if item.get('department_code'):
                        department = Department.objects.get(code=item['department_code'], institution=institution)
                    
                    subject, created = Subject.objects.update_or_create(
                        institution=institution,
                        code=item['code'],
                        defaults={
                            'name': item['name'],
                            'subject_type': item.get('subject_type', 'core'),
                            'difficulty_level': item.get('difficulty_level', 'basic'),
                            'credits': item.get('credits', 3),
                            'department': department,
                            'description': item.get('description', ''),
                            'is_active': item.get('is_active', True)
                        }
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'Successfully loaded subject: {item["name"]}')
                    )
                    
                except (Institution.DoesNotExist, Department.DoesNotExist) as e:
                    self.stdout.write(
                        self.style.WARNING(f'Related object not found for subject {item["name"]}: {str(e)}')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error loading subject {item["name"]}: {str(e)}')
                    )
                    
        except FileNotFoundError:
            self.stdout.write(
                self.style.WARNING('Subjects JSON file not found')
            )
            
                
    def load_timetables(self):
        file_path = os.path.join('apps', 'academics', 'data', 'timetables.json')
        
        try:
            with open(file_path, 'r') as file:
                data = json.load(file)
                
            for item in data:
                try:
                    institution = Institution.objects.get(code=item['institution_code'])
                    academic_year = AcademicYear.objects.get(
                        institution=institution, 
                        name=item['academic_year_name']
                    )
                    class_obj = Class.objects.get(
                        institution=institution, 
                        code=item['class_code']
                    )
                    section = Section.objects.get(
                        institution=institution,
                        class_name=class_obj,
                        name=item['section_name']
                    )
                    subject = Subject.objects.get(
                        institution=institution,
                        code=item['subject_code']
                    )
                    
                    # Look up teacher by employee_id instead of code
                    teacher = Teacher.objects.get(employee_id=item['teacher_employee_id'])
                    
                    Timetable.objects.update_or_create(
                        institution=institution,
                        academic_year=academic_year,
                        class_name=class_obj,
                        section=section,
                        day=item['day'],
                        period=item['period'],
                        defaults={
                            'subject': subject,
                            'teacher': teacher,
                            'start_time': item['start_time'],
                            'end_time': item['end_time'],
                            'room': item.get('room', ''),
                            'is_active': item.get('is_active', True)
                        }
                    )
                    
                    self.stdout.write(
                        self.style.SUCCESS(f'Successfully loaded timetable: {class_obj.name} - {item["day"]} Period {item["period"]}')
                    )
                    
                except (Institution.DoesNotExist, AcademicYear.DoesNotExist, 
                        Class.DoesNotExist, Section.DoesNotExist, 
                        Subject.DoesNotExist, Teacher.DoesNotExist) as e:
                    self.stdout.write(
                        self.style.WARNING(f'Related object not found for timetable: {str(e)}')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error loading timetable: {str(e)}')
                    )
                    
        except FileNotFoundError:
            self.stdout.write(
                self.style.WARNING('Timetables JSON file not found')
            )