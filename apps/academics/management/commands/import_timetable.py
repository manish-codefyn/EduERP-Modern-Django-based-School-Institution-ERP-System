import os
import json
import uuid
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_time
from apps.academics.models import Timetable, AcademicYear, Class, Section, Subject
from apps.teachers.models import Teacher
from apps.organization.models import Institution


class Command(BaseCommand):
    help = 'Import timetable data from JSON file (apps/academics/data/timetable.json)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='timetable.json',
            help='JSON file name inside apps/academics/data/ (default: timetable.json)'
        )
        parser.add_argument(
            '--institution',
            type=str,
            required=True,
            help='Institution ID or name'
        )
        parser.add_argument(
            '--academic-year',
            type=str,
            required=True,
            help='Academic Year ID or name'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate import without saving'
        )

    def handle(self, *args, **options):
        # Resolve file path
        base_dir = os.path.join(settings.BASE_DIR, 'apps', 'academics', 'data')
        json_file = os.path.join(base_dir, options['file'])

        institution_ref = options['institution']
        academic_year_ref = options['academic_year']
        dry_run = options['dry_run']

        try:
            # Load and parse JSON file
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if not isinstance(data, list):
                raise CommandError('JSON file should contain an array of timetable entries')

            # Get institution
            try:
                if uuid.UUID(institution_ref):
                    institution = Institution.objects.get(id=institution_ref)
            except (ValueError, Institution.DoesNotExist):
                institution = Institution.objects.get(name=institution_ref)

            # Get academic year
            try:
                if uuid.UUID(academic_year_ref):
                    academic_year = AcademicYear.objects.get(id=academic_year_ref)
            except (ValueError, AcademicYear.DoesNotExist):
                academic_year = AcademicYear.objects.get(name=academic_year_ref)

            success_count, error_count, errors = 0, 0, []

            # Process entries
            for i, entry_data in enumerate(data, 1):
                try:
                    self.process_entry(entry_data, institution, academic_year, dry_run)
                    success_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Processed entry {i}: '
                            f'{entry_data.get("class_name", "N/A")} - '
                            f'{entry_data.get("day", "N/A")} - '
                            f'Period {entry_data.get("period", "N/A")}'
                        )
                    )
                except Exception as e:
                    error_count += 1
                    error_msg = f'Error processing entry {i}: {str(e)}'
                    errors.append(error_msg)
                    self.stdout.write(self.style.ERROR(error_msg))

            # Summary
            self.stdout.write('\n' + '=' * 50)
            self.stdout.write(f'Import Summary:')
            self.stdout.write(f'Successfully processed: {success_count}')
            self.stdout.write(f'Errors: {error_count}')

            if errors and not dry_run:
                self.stdout.write('\nErrors encountered:')
                for error in errors:
                    self.stdout.write(self.style.ERROR(f'  - {error}'))

            if dry_run:
                self.stdout.write(self.style.WARNING('\nDRY RUN: No data was saved to database'))
            else:
                self.stdout.write(self.style.SUCCESS('\nImport completed successfully!'))

        except FileNotFoundError:
            raise CommandError(f'File not found: {json_file}')
        except json.JSONDecodeError:
            raise CommandError(f'Invalid JSON format in file: {json_file}')
        except Institution.DoesNotExist:
            raise CommandError(f'Institution not found: {institution_ref}')
        except AcademicYear.DoesNotExist:
            raise CommandError(f'Academic Year not found: {academic_year_ref}')
        except Exception as e:
            raise CommandError(f'Unexpected error: {str(e)}')

    def process_entry(self, entry_data, institution, academic_year, dry_run):
        """Process a single timetable entry with validation"""

        # Validate required fields
        required_fields = [
            'class_name', 'section', 'day', 'period',
            'subject', 'teacher', 'start_time', 'end_time'
        ]
        for field in required_fields:
            if field not in entry_data:
                raise ValueError(f'Missing required field: {field}')

        # Validate day
        day = entry_data['day'].strip().lower()
        valid_days = [choice[0].lower() for choice in Timetable.DAY_CHOICES]
        if day not in valid_days:
            raise ValueError(f'Invalid day: {day}. Must be one of: {valid_days}')

        # Validate period
        try:
            period = int(entry_data['period'])
            if period <= 0:
                raise ValueError('Period must be a positive integer')
        except (ValueError, TypeError):
            raise ValueError('Period must be a valid integer')

        # Validate times
        start_time = parse_time(entry_data['start_time'])
        if not start_time:
            raise ValueError('Invalid start_time format. Use HH:MM:SS or HH:MM')

        end_time = parse_time(entry_data['end_time'])
        if not end_time:
            raise ValueError('Invalid end_time format. Use HH:MM:SS or HH:MM')

        if start_time >= end_time:
            raise ValueError('End time must be after start time')

        # Get related objects
        try:
            class_obj = Class.objects.get(name=entry_data['class_name'], institution=institution)
        except Class.DoesNotExist:
            raise ValueError(f'Class not found: {entry_data["class_name"]}')

        try:
            section = Section.objects.get(name=entry_data['section'], class_name=class_obj)
        except Section.DoesNotExist:
            raise ValueError(f'Section not found: {entry_data["section"]} for class {class_obj.name}')

        try:
            subject = Subject.objects.get(name=entry_data['subject'], institution=institution)
        except Subject.DoesNotExist:
            raise ValueError(f'Subject not found: {entry_data["subject"]}')

        try:
            parts = entry_data['teacher'].split()
            first_name = parts[0]
            last_name = " ".join(parts[1:]) if len(parts) > 1 else ''
            teacher = Teacher.objects.get(
                user__first_name=first_name,
                user__last_name=last_name,
                institution=institution
            )
        except Teacher.DoesNotExist:
            raise ValueError(f'Teacher not found: {entry_data["teacher"]}')

        # Save (update or create)
        if not dry_run:
            with transaction.atomic():
                Timetable.objects.update_or_create(
                    institution=institution,
                    academic_year=academic_year,
                    class_name=class_obj,
                    section=section,
                    day=day,
                    period=period,
                    defaults={
                        'subject': subject,
                        'teacher': teacher,
                        'start_time': start_time,
                        'end_time': end_time,
                        'room': entry_data.get('room', ''),
                        'is_active': entry_data.get('is_active', True)
                    }
                )
