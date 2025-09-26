# apps/finance/management/commands/generate_demo_data.py
import json
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from apps.organization.models import Institution
from apps.academics.models import AcademicYear, Class
from apps.students.models import Student
from apps.finance.models import FeeStructure, FeeInvoice, Payment
from django.utils.translation import gettext_lazy as _


class Command(BaseCommand):
    help = 'Generate comprehensive demo data for finance app'

    def add_arguments(self, parser):
        parser.add_argument(
            '--institution',
            type=str,
            default='Demo School',
            help='Institution name for demo data'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before generating new data'
        )

    def handle(self, *args, **options):
        institution_name = options['institution']
        clear_existing = options['clear']

        # Get or create institution
        institution, created = Institution.objects.get_or_create(
            name=institution_name,
            defaults={
                'code': 'DEMO',
                'address': '123 Demo Street, Demo City',
                'phone': '+1-555-0123',
                'email': 'info@demoschool.edu',
                'website': 'www.demoschool.edu',
                'is_active': True
            }
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'Created institution: {institution.name}'))

        if clear_existing:
            # Clear existing data
            Payment.objects.filter(institution=institution).delete()
            FeeInvoice.objects.filter(institution=institution).delete()
            FeeStructure.objects.filter(institution=institution).delete()
            self.stdout.write(self.style.WARNING('Cleared existing finance data'))

        # First load fee structures
        self.stdout.write(self.style.SUCCESS('Loading fee structures...'))
        from django.core.management import call_command
        call_command('load_fee_structures', institution=institution.name)

        # Create academic year if not exists
        academic_year, created = AcademicYear.objects.get_or_create(
            name='2024-2025',
            institution=institution,
            defaults={
                'start_date': '2024-06-01',
                'end_date': '2025-05-31',
                'is_current': True
            }
        )

        # Create some demo classes if they don't exist
        classes = []
        for i in range(1, 11):
            class_obj, created = Class.objects.get_or_create(
                name=f'Class {i}',
                institution=institution,
                defaults={'display_order': i, 'is_active': True}
            )
            classes.append(class_obj)

        # Create demo students if they don't exist
        students = []
        for i in range(1, 21):
            student, created = Student.objects.get_or_create(
                student_id=f'STU{i:03d}',
                institution=institution,
                defaults={
                    'first_name': f'Student{i}',
                    'last_name': 'Demo',
                    'current_class': classes[(i-1) % 10],
                    'roll_number': i,
                    'date_of_birth': f'201{5 + (i % 5)}-{(i % 12) + 1:02d}-{(i % 28) + 1:02d}',
                    'gender': 'M' if i % 2 == 0 else 'F',
                    'is_active': True
                }
            )
            students.append(student)

        # Create fee invoices for students
        self.stdout.write(self.style.SUCCESS('Creating demo fee invoices...'))
        for student in students:
            fee_structures = FeeStructure.objects.filter(
                institution=institution,
                academic_year=academic_year,
                class_name=student.current_class,
                is_active=True
            )

            total_amount = sum(fs.amount for fs in fee_structures)
            
            if total_amount > 0:
                invoice = FeeInvoice.objects.create(
                    institution=institution,
                    student=student,
                    academic_year=academic_year,
                    issue_date='2024-06-01',
                    due_date='2024-06-30',
                    total_amount=total_amount,
                    status='issued'
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Created invoice {invoice.invoice_number} for {student}')
                )

        # Create some demo payments
        self.stdout.write(self.style.SUCCESS('Creating demo payments...'))
        invoices = FeeInvoice.objects.filter(institution=institution, status='issued')[:10]
        
        for i, invoice in enumerate(invoices):
            payment_status = 'completed' if i % 2 == 0 else 'partially_paid'
            amount_paid = invoice.total_amount if i % 2 == 0 else invoice.total_amount * 0.5
            
            payment = Payment.objects.create(
                institution=institution,
                student=invoice.student,
                invoice=invoice,
                payment_mode='cash' if i % 3 == 0 else 'bank_transfer',
                payment_date='2024-06-15',
                amount=invoice.total_amount,
                amount_paid=amount_paid,
                status=payment_status,
                remarks=f'Demo payment #{i+1}'
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'Created payment {payment.payment_number} for {invoice.student}')
            )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully generated demo data for {institution.name}\n'
                f'- Fee Structures: {FeeStructure.objects.filter(institution=institution).count()}\n'
                f'- Fee Invoices: {FeeInvoice.objects.filter(institution=institution).count()}\n'
                f'- Payments: {Payment.objects.filter(institution=institution).count()}'
            )
        )