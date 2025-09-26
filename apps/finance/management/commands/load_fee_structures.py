# apps/finance/management/commands/load_fee_structures.py
import json
import os
import re
from django.core.management.base import BaseCommand
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from apps.organization.models import Institution
from apps.academics.models import AcademicYear, Class
from apps.finance.models import FeeStructure


class Command(BaseCommand):
    help = 'Load demo fee structure data from JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='Specify custom JSON file path',
            default='apps/finance/data/fee_structure_demo.json'
        )
        parser.add_argument(
            '--institution',
            type=str,
            help='Institution ID or name to associate with fee structures',
            default='default'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing fee structures before loading',
        )

    def handle(self, *args, **options):
        file_path = options['file']
        institution_identifier = options['institution']
        clear_existing = options['clear']

        # Get absolute file path
        if not file_path.startswith('/'):
            file_path = os.path.join(settings.BASE_DIR, file_path)

        # Check if file exists
        if not os.path.exists(file_path):
            self.stderr.write(self.style.ERROR(f'File not found: {file_path}'))
            return

        # Get or create institution
        try:
            if institution_identifier.isdigit():
                institution = Institution.objects.get(id=int(institution_identifier))
            else:
                # Try to get by name, or create if doesn't exist
                institution, created = Institution.objects.get_or_create(
                    name=institution_identifier,
                    defaults={
                        'code': institution_identifier.upper()[:10],
                        'address': 'Demo address',
                        'phone': '000-000-0000',
                        'email': f'info@{institution_identifier.lower()}.com',
                        'is_active': True
                    }
                )
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f'Created new institution: {institution.name}')
                    )
        except Institution.DoesNotExist:
            self.stderr.write(self.style.ERROR(f'Institution not found: {institution_identifier}'))
            return

        # Clear existing fee structures if requested
        if clear_existing:
            deleted_count, _ = FeeStructure.objects.filter(institution=institution).delete()
            self.stdout.write(
                self.style.WARNING(f'Deleted {deleted_count} existing fee structures')
            )

        # Load and parse JSON data
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.stderr.write(self.style.ERROR(f'Invalid JSON file: {e}'))
            return

        fee_structures_data = data.get('fee_structures', [])
        
        if not fee_structures_data:
            self.stderr.write(self.style.ERROR('No fee structures found in JSON file'))
            return

        created_count = 0
        updated_count = 0
        skipped_count = 0

        for fee_data in fee_structures_data:
            try:
                # Get academic year
                academic_year_name = fee_data.get('academic_year')
                academic_year, created = AcademicYear.objects.get_or_create(
                    name=academic_year_name,
                    institution=institution,
                    defaults={
                        'start_date': f'{academic_year_name.split("-")[0]}-06-01',
                        'end_date': f'{academic_year_name.split("-")[1]}-05-31',
                        'is_current': True
                    }
                )
                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f'Created academic year: {academic_year.name}')
                    )

                # Get class
                class_name = fee_data.get('class_name')
                
                if class_name == 'All Classes':
                    # Create fee structure for all classes
                    classes = Class.objects.filter(institution=institution, is_active=True)
                    if not classes.exists():
                        self.stdout.write(
                            self.style.WARNING('No classes found for institution. Creating a default class.')
                        )
                        default_class, created = Class.objects.get_or_create(
                            name='Class 1',
                            institution=institution,
                            defaults={'is_active': True}
                        )
                        classes = [default_class]
                        
                elif 'Class' in class_name and '-' in class_name:
                    # Handle class ranges like "Class 6-10"
                    class_range = class_name.replace('Class', '').strip()
                    start_class, end_class = map(str.strip, class_range.split('-'))
                    
                    # Extract numbers from class names
                    start_num = int(re.search(r'\d+', start_class).group()) if re.search(r'\d+', start_class) else 0
                    end_num = int(re.search(r'\d+', end_class).group()) if re.search(r'\d+', end_class) else 0
                    
                    classes = []
                    for num in range(start_num, end_num + 1):
                        class_name_str = f'Class {num}'
                        class_obj, created = Class.objects.get_or_create(
                            name=class_name_str,
                            institution=institution,
                            defaults={'is_active': True}
                        )
                        classes.append(class_obj)
                        if created:
                            self.stdout.write(
                                self.style.SUCCESS(f'Created class: {class_obj.name}')
                            )
                else:
                    # Single class
                    class_obj, created = Class.objects.get_or_create(
                        name=class_name,
                        institution=institution,
                        defaults={'is_active': True}
                    )
                    if created:
                        self.stdout.write(
                            self.style.SUCCESS(f'Created class: {class_obj.name}')
                        )
                    classes = [class_obj]

                # Create fee structure for each class
                for class_obj in classes:
                    fee_structure, created = FeeStructure.objects.get_or_create(
                        institution=institution,
                        academic_year=academic_year,
                        class_name=class_obj,
                        defaults={
                            'name': fee_data.get('name'),
                            'amount': fee_data.get('amount'),
                            'is_active': fee_data.get('is_active', True)
                        }
                    )

                    if created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'Created fee structure: {fee_structure.name} for {class_obj.name}')
                        )
                    else:
                        # Update existing fee structure
                        fee_structure.amount = fee_data.get('amount')
                        fee_structure.is_active = fee_data.get('is_active', True)
                        fee_structure.save()
                        updated_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'Updated fee structure: {fee_structure.name} for {class_obj.name}')
                        )

            except Exception as e:
                skipped_count += 1
                self.stderr.write(
                    self.style.ERROR(f'Error processing fee structure {fee_data.get("name")}: {e}')
                )
                continue

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully loaded fee structures: {created_count} created, '
                f'{updated_count} updated, {skipped_count} skipped'
            )
        )