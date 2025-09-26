from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import ListView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, Sum, Q ,Avg , Max ,Min,ExpressionWrapper
from django.db import  models
from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta
import csv
from io import StringIO, BytesIO
import xlsxwriter
from utils.utils import render_to_pdf, export_pdf_response
from apps.core.utils import get_user_institution
from apps.students.models import Student
from apps.academics.models import Section,Class,AcademicYear,Subject
from apps.students.forms import StudentExportForm,StudentFilterForm
from apps.teachers.models import Teacher
from apps.attendance.models import Attendance
from apps.finance.models import Payment, FeeInvoice,FeeStructure
from apps.examination.models import ExamResult
from .forms import (AttendanceFilterForm, AttendanceExportForm,FinancialExportForm,
                    AcademicExportForm,AcademicFilterForm,
                    FinancialFilterForm)


class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'reports/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        
        # Student statistics
        total_students = Student.objects.filter(institution=institution, status="ACTIVE").count()
        new_students = Student.objects.filter(
            institution=institution,
            status="ACTIVE",
            created_at__date=timezone.now().date()
        ).count()
        
        # Teacher statistics
        total_teachers = Teacher.objects.filter(institution=institution, is_active=True).count()
        
        # Attendance statistics
        today_attendance = Attendance.objects.filter(
            institution=institution,
            date=timezone.now().date()
        ).aggregate(
            present=Count('id', filter=Q(status='present')),
            total=Count('id')
        )
        attendance_percentage = (today_attendance['present'] / today_attendance['total'] * 100) if today_attendance['total'] > 0 else 0
        
        # Finance statistics
        today_payments = Payment.objects.filter(
            institution=institution,
            payment_date=timezone.now().date(),
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        outstanding_fees = FeeInvoice.objects.filter(
            institution=institution,
            status__in=['issued', 'partial']
        ).aggregate(
            total=Sum('total_amount'),
            paid=Sum('paid_amount')
        )
        outstanding_amount = (outstanding_fees['total'] or 0) - (outstanding_fees['paid'] or 0)
    
        # Update context
        context.update({
            'total_students': total_students,
            'new_students': new_students,
            'total_teachers': total_teachers,
            'attendance_percentage': round(attendance_percentage, 2),
            'today_payments': today_payments,
            'outstanding_amount': outstanding_amount,
           
        })
        
        return context



class StudentReportView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'reports/student_report.html'
    permission_required = 'reports.view_student_reports'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)

        # Initialize filter form with GET data
        filter_form = StudentFilterForm(self.request.GET)
        
        # Apply institution filtering to querysets in the form
        filter_form.fields['student_class'].queryset = Class.objects.filter(institution=institution)
        filter_form.fields['section'].queryset = Section.objects.filter(institution=institution)
        filter_form.fields['academic_year'].queryset = AcademicYear.objects.filter(institution=institution)

        students = Student.objects.filter(institution=institution)

        # Apply filters if form is valid
        if filter_form.is_valid():
            cleaned_data = filter_form.cleaned_data
            
            if cleaned_data.get('admission_number'):
                students = students.filter(admission_number__icontains=cleaned_data['admission_number'])
            if cleaned_data.get('first_name'):
                students = students.filter(user__first_name__icontains=cleaned_data['first_name'])
            if cleaned_data.get('last_name'):
                students = students.filter(user__last_name__icontains=cleaned_data['last_name'])
            if cleaned_data.get('student_class'):
                students = students.filter(current_class=cleaned_data['student_class'])
            if cleaned_data.get('section'):
                students = students.filter(section=cleaned_data['section'])
            if cleaned_data.get('academic_year'):
                students = students.filter(academic_year=cleaned_data['academic_year'])
            if cleaned_data.get('status'):
                students = students.filter(status=cleaned_data['status'])
            if cleaned_data.get('gender'):
                students = students.filter(gender=cleaned_data['gender'])
            if cleaned_data.get('category'):
                students = students.filter(category=cleaned_data['category'])
            if cleaned_data.get('religion'):
                students = students.filter(religion=cleaned_data['religion'])
            
            # Boolean filters
            if cleaned_data.get('has_hostel') == 'yes':
                students = students.filter(has_hostel=True)
            elif cleaned_data.get('has_hostel') == 'no':
                students = students.filter(has_hostel=False)
                
            if cleaned_data.get('has_disability') == 'yes':
                students = students.filter(has_disability=True)
            elif cleaned_data.get('has_disability') == 'no':
                students = students.filter(has_disability=False)
                
            has_transport = cleaned_data.get('has_transport')

            if has_transport == 'yes':
                # Only students with an active transport record
                students = students.filter(transport__isnull=False, transport__is_active=True)
            elif has_transport == 'no':
                # Students without transport
                students = students.filter(transport__isnull=True)

        context['students'] = students.select_related('user', 'current_class', 'section', 'academic_year')
        context['filter_form'] = filter_form
        context['search_form'] = StudentExportForm()
        
        # Default fields to include
        context['student_fields'] = [
            ('admission_number', 'Admission Number'),
            ('full_name', 'Full Name'),
            ('current_class', 'Class'),
            ('section', 'Section'),
            ('gender', 'Gender'),
            ('phone', 'Contact'),
            ('status', 'Status'),
            ('academic_year', 'Academic Year'),
        ]
        return context

    def get(self, request, *args, **kwargs):
        # Export functionality
        format_type = request.GET.get('format', '').lower()
        if not format_type:
            return super().get(request, *args, **kwargs)

        context = self.get_context_data(**kwargs)
        students = context['students']
        selected_columns = request.GET.getlist('columns')  # list of selected fields
        filename = f"student_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        organization = get_user_institution(request.user)

        if format_type == 'csv':
            return self.export_csv(students, filename, organization, selected_columns)
        elif format_type == 'excel':
            return self.export_excel(students, filename, organization, selected_columns)
        elif format_type == 'pdf':
            return self.export_pdf(students, filename, organization, selected_columns)

        return HttpResponse("Invalid format specified", status=400)

    def export_csv(self, students, filename, organization, columns):
        buffer = StringIO()
        writer = csv.writer(buffer)

        headers = [label for field, label in self.get_context_data()['student_fields'] if field in columns]
        writer.writerow(headers)

        for s in students:
            row = []
            for field, label in self.get_context_data()['student_fields']:
                if field in columns:
                    value = getattr(s, field) if hasattr(s, field) else ''
                    if field == 'full_name':
                        value = s.user.get_full_name()
                    elif field == 'current_class':
                        value = s.current_class.name if s.current_class else ''
                    elif field == 'section':
                        value = s.section.name if s.section else ''
                    elif field == 'gender':
                        value = s.get_gender_display()
                    elif field == 'phone':
                        value = s.user.phone
                    elif field == 'status':
                        value = 'Active' if s.status == 'ACTIVE' else 'Inactive'
                    elif field == 'academic_year':
                        value = s.academic_year.name if s.academic_year else ''
                    row.append(value)
            writer.writerow(row)

        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response

    def export_excel(self, students, filename, organization, columns):
        buffer = BytesIO()
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet("Students")
            header_format = workbook.add_format({
                "bold": True,
                "bg_color": "#2c3e50",
                "font_color": "white",
                "border": 1,
                "align": "center",
                "valign": "vcenter"
            })
            headers = [label for field, label in self.get_context_data()['student_fields'] if field in columns]
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            for row_idx, s in enumerate(students, start=1):
                row = []
                for field, label in self.get_context_data()['student_fields']:
                    if field in columns:
                        value = getattr(s, field) if hasattr(s, field) else ''
                        if field == 'full_name':
                            value = s.user.get_full_name()
                        elif field == 'current_class':
                            value = s.current_class.name if s.current_class else ''
                        elif field == 'section':
                            value = s.section.name if s.section else ''
                        elif field == 'gender':
                            value = s.get_gender_display()
                        elif field == 'phone':
                            value = s.user.phone
                        elif field == 'status':
                            value = 'Active' if s.status == 'ACTIVE' else 'Inactive'
                        elif field == 'academic_year':
                            value = s.academic_year.name if s.academic_year else ''
                        row.append(value)
                for col_idx, value in enumerate(row):
                    worksheet.write(row_idx, col_idx, value)

        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return response

    def export_pdf(self, students, filename, organization, columns):
        # PDF context with selected columns
        context = {
            "students": students,
            "columns": columns,
            "total_count": students.count(),
            "export_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": "Student Report",
        }
        pdf_bytes = render_to_pdf("reports/export/student_report_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)


class AttendanceReportView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'reports/attendance_report.html'
    permission_required = 'reports.view_attendance_reports'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)

        # Initialize filter form with GET data
        filter_form = AttendanceFilterForm(self.request.GET)
        filter_form.fields['student_class'].queryset = Class.objects.filter(institution=institution)
        filter_form.fields['section'].queryset = Section.objects.filter(institution=institution)
        filter_form.fields['academic_year'].queryset = AcademicYear.objects.filter(institution=institution)

        attendance_records = Attendance.objects.filter(institution=institution).select_related(
            'student__user', 'student__current_class', 'student__section', 'student__academic_year'
        )

        if filter_form.is_valid():
            data = filter_form.cleaned_data
            if data.get('student'):
                attendance_records = attendance_records.filter(student=data['student'])
            if data.get('student_class'):
                attendance_records = attendance_records.filter(student__current_class=data['student_class'])
            if data.get('section'):
                attendance_records = attendance_records.filter(student__section=data['section'])
            if data.get('academic_year'):
                attendance_records = attendance_records.filter(student__academic_year=data['academic_year'])
            if data.get('status'):
                attendance_records = attendance_records.filter(status=data['status'])
            if data.get('start_date'):
                attendance_records = attendance_records.filter(date__gte=data['start_date'])
            if data.get('end_date'):
                attendance_records = attendance_records.filter(date__lte=data['end_date'])

        context['attendance_records'] = attendance_records
        context['filter_form'] = filter_form
        context['export_form'] = AttendanceExportForm()
        context['attendance_fields'] = [
            ('student', 'Student Name'),
            ('current_class', 'Class'),
            ('section', 'Section'),
            ('academic_year', 'Academic Year'),
            ('date', 'Date'),
            ('status', 'Status'),
        ]
        return context

    def get(self, request, *args, **kwargs):
        format_type = request.GET.get('format', '').lower()
        if not format_type:
            return super().get(request, *args, **kwargs)

        context = self.get_context_data(**kwargs)
        records = context['attendance_records']
        selected_columns = request.GET.getlist('columns')
        filename = f"attendance_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        organization = get_user_institution(request.user)

        if format_type == 'csv':
            return self.export_csv(records, filename, selected_columns)
        elif format_type == 'excel':
            return self.export_excel(records, filename, selected_columns)
        elif format_type == 'pdf':
            return self.export_pdf(records, filename, organization, selected_columns)

        return HttpResponse("Invalid format specified", status=400)

    def export_csv(self, records, filename, columns):
        buffer = StringIO()
        writer = csv.writer(buffer)
        headers = [label for field, label in self.get_context_data()['attendance_fields'] if field in columns]
        writer.writerow(headers)

        for r in records:
            row = []
            for field, label in self.get_context_data()['attendance_fields']:
                if field in columns:
                    if field == 'student':
                        value = r.student.user.get_full_name()
                    elif field == 'current_class':
                        value = r.student.current_class.name if r.student.current_class else ''
                    elif field == 'section':
                        value = r.student.section.name if r.student.section else ''
                    elif field == 'academic_year':
                        value = r.student.academic_year.name if r.student.academic_year else ''
                    elif field == 'date':
                        value = r.date.strftime('%Y-%m-%d')
                    elif field == 'status':
                        value = r.get_status_display()
                    else:
                        value = getattr(r, field, '')
                    row.append(value)
            writer.writerow(row)

        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response

    def export_excel(self, records, filename, columns):
        buffer = BytesIO()
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet("Attendance")
            header_format = workbook.add_format({
                "bold": True,
                "bg_color": "#2c3e50",
                "font_color": "white",
                "border": 1,
                "align": "center",
                "valign": "vcenter"
            })

            headers = [label for field, label in self.get_context_data()['attendance_fields'] if field in columns]
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            for row_idx, r in enumerate(records, start=1):
                row = []
                for field, label in self.get_context_data()['attendance_fields']:
                    if field in columns:
                        if field == 'student':
                            value = r.student.user.get_full_name()
                        elif field == 'current_class':
                            value = r.student.current_class.name if r.student.current_class else ''
                        elif field == 'section':
                            value = r.student.section.name if r.student.section else ''
                        elif field == 'academic_year':
                            value = r.student.academic_year.name if r.student.academic_year else ''
                        elif field == 'date':
                            value = r.date.strftime('%Y-%m-%d')
                        elif field == 'status':
                            value = r.get_status_display()
                        else:
                            value = getattr(r, field, '')
                        row.append(value)
                for col_idx, value in enumerate(row):
                    worksheet.write(row_idx, col_idx, value)

        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return response

    def export_pdf(self, records, filename, organization, columns):
        context = {
            "attendance_records": records,
            "columns": columns,
            "total_count": records.count(),
            "export_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": "Attendance Report",
        }
        pdf_bytes = render_to_pdf("reports/export/attendance_report_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)

class FinancialReportView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'reports/financial_report.html'
    permission_required = 'reports.view_financial_reports'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)

        # Initialize filter form with GET data
        filter_form = FinancialFilterForm(self.request.GET)
        
        # Apply institution filtering to querysets in the form
        filter_form.fields['student_class'].queryset = Class.objects.filter(institution=institution)
        filter_form.fields['academic_year'].queryset = AcademicYear.objects.filter(institution=institution)
        filter_form.fields['fee_type'].queryset = FeeStructure.objects.filter(institution=institution)

        payments = Payment.objects.filter(institution=institution).select_related(
            'student__user', 'student__current_class', 'student__section', 
            'student__academic_year', 'invoice'
        )

        # Apply filters if form is valid
        if filter_form.is_valid():
            cleaned_data = filter_form.cleaned_data
            
            if cleaned_data.get('start_date'):
                payments = payments.filter(payment_date__gte=cleaned_data['start_date'])
            if cleaned_data.get('end_date'):
                payments = payments.filter(payment_date__lte=cleaned_data['end_date'])
            if cleaned_data.get('student_class'):
                payments = payments.filter(student__current_class=cleaned_data['student_class'])
            if cleaned_data.get('academic_year'):
                payments = payments.filter(student__academic_year=cleaned_data['academic_year'])
            if cleaned_data.get('fee_type'):
                payments = payments.filter(invoice__fee_type=cleaned_data['fee_type'])
            if cleaned_data.get('payment_mode'):
                payments = payments.filter(payment_mode=cleaned_data['payment_mode'])
            if cleaned_data.get('status'):
                payments = payments.filter(status=cleaned_data['status'])
            if cleaned_data.get('student'):
                payments = payments.filter(student=cleaned_data['student'])

        # Payment statistics by mode
        payment_stats = (
            payments.values("payment_mode")
            .annotate(
                total_amount=Sum("amount"),
                total_paid=Sum("amount_paid"),
                count=Count("id"),
            )
        )

        # Monthly trend
        monthly_trend = payments.extra(
            select={'month': "EXTRACT(month FROM payment_date)", 'year': "EXTRACT(year FROM payment_date)"}
        ).values('year', 'month').annotate(
            total_amount=Sum('amount'),
            total_paid=Sum('amount_paid'),
            payment_count=Count('id')
        ).order_by('year', 'month')

        # Status breakdown
        status_breakdown = payments.values('status').annotate(
            total_amount=Sum('amount'),
            total_paid=Sum('amount_paid'),
            count=Count('id')
        ).order_by('-total_amount')

        # Calculate overall totals
        overall_totals = payments.aggregate(
            total_amount=Sum('amount'),
            total_paid=Sum('amount_paid'),
            total_count=Count('id')
        )
        total_amount = overall_totals['total_amount'] or 0

        # Add percentage values for template
        for stat in payment_stats:
            if total_amount > 0:
                stat['percentage'] = (stat['total_amount'] or 0) / total_amount * 100
            else:
                stat['percentage'] = 0

        for stat in status_breakdown:
            if total_amount > 0:
                stat['percentage'] = (stat['total_amount'] or 0) / total_amount * 100
            else:
                stat['percentage'] = 0

            context.update({
            'payments': payments,
            'payment_stats': payment_stats,
            'monthly_trend': monthly_trend,
            'status_breakdown': status_breakdown,
            'total_amount': total_amount,
            'total_paid': overall_totals['total_paid'] or 0,
            'total_count': overall_totals['total_count'] or 0,
            'total_balance': total_amount - (overall_totals['total_paid'] or 0),
            'filter_form': filter_form,
            'export_form': FinancialExportForm(),
            'financial_fields': [
                ('payment_number', 'Payment Number'),
                ('student', 'Student Name'),
                ('admission_number', 'Admission Number'),
                ('current_class', 'Class'),
                ('section', 'Section'),
                ('invoice_number', 'Invoice Number'),
                ('amount', 'Total Amount'),
                ('amount_paid', 'Amount Paid'),
                ('balance', 'Balance'),
                ('payment_mode', 'Payment Mode'),
                ('payment_date', 'Payment Date'),
                ('reference_number', 'Reference Number'),
                ('status', 'Status'),
                ('academic_year', 'Academic Year'),
                ('remarks', 'Remarks'),
            ]
        })

        
        return context

    def get(self, request, *args, **kwargs):
        # Export functionality
        format_type = request.GET.get('format', '').lower()
        if not format_type:
            return super().get(request, *args, **kwargs)

        context = self.get_context_data(**kwargs)
        payments = context['payments']
        selected_columns = request.GET.getlist('columns')
        filename = f"financial_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        organization = get_user_institution(request.user)

        if format_type == 'csv':
            return self.export_csv(payments, filename, organization, selected_columns)
        elif format_type == 'excel':
            return self.export_excel(payments, filename, organization, selected_columns)
        elif format_type == 'pdf':
            return self.export_pdf(payments, filename, organization, selected_columns)

        return HttpResponse("Invalid format specified", status=400)

    def export_csv(self, payments, filename, organization, columns):
        buffer = StringIO()
        writer = csv.writer(buffer)

        headers = [label for field, label in self.get_context_data()['financial_fields'] if field in columns]
        writer.writerow(headers)

        for payment in payments:
            row = []
            for field, label in self.get_context_data()['financial_fields']:
                if field in columns:
                    if field == 'student':
                        value = payment.student.user.get_full_name() if payment.student and payment.student.user else 'N/A'
                    elif field == 'admission_number':
                        value = payment.student.admission_number if payment.student else 'N/A'
                    elif field == 'current_class':
                        value = payment.student.current_class.name if payment.student and payment.student.current_class else ''
                    elif field == 'section':
                        value = payment.student.section.name if payment.student and payment.student.section else ''
                    elif field == 'invoice_number':
                        value = payment.invoice.invoice_number if payment.invoice else 'N/A'
                    elif field == 'amount':
                        value = str(payment.amount)
                    elif field == 'amount_paid':
                        value = str(payment.amount_paid)
                    elif field == 'balance':
                        value = str(payment.balance)
                    elif field == 'payment_mode':
                        value = payment.get_payment_mode_display()
                    elif field == 'payment_date':
                        value = payment.payment_date.strftime('%Y-%m-%d') if payment.payment_date else ''
                    elif field == 'reference_number':
                        value = payment.reference_number
                    elif field == 'status':
                        value = payment.get_status_display()
                    elif field == 'academic_year':
                        value = payment.student.academic_year.name if payment.student and payment.student.academic_year else ''
                    elif field == 'remarks':
                        value = payment.remarks
                    elif field == 'payment_number':
                        value = payment.payment_number
                    else:
                        value = getattr(payment, field, '')
                    row.append(value)
            writer.writerow(row)

        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response

    def export_excel(self, payments, filename, organization, columns):
        buffer = BytesIO()
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet("Financial Report")
            header_format = workbook.add_format({
                "bold": True,
                "bg_color": "#2c3e50",
                "font_color": "white",
                "border": 1,
                "align": "center",
                "valign": "vcenter"
            })
            
            # Currency format for amount columns
            currency_format = workbook.add_format({'num_format': '#,##0.00'})

            headers = [label for field, label in self.get_context_data()['financial_fields'] if field in columns]
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            for row_idx, payment in enumerate(payments, start=1):
                row = []
                for field, label in self.get_context_data()['financial_fields']:
                    if field in columns:
                        if field == 'student':
                            value = payment.student.user.get_full_name() if payment.student and payment.student.user else 'N/A'
                        elif field == 'admission_number':
                            value = payment.student.admission_number if payment.student else 'N/A'
                        elif field == 'current_class':
                            value = payment.student.current_class.name if payment.student and payment.student.current_class else ''
                        elif field == 'section':
                            value = payment.student.section.name if payment.student and payment.student.section else ''
                        elif field == 'invoice_number':
                            value = payment.invoice.invoice_number if payment.invoice else 'N/A'
                        elif field == 'amount':
                            value = float(payment.amount)
                        elif field == 'amount_paid':
                            value = float(payment.amount_paid)
                        elif field == 'balance':
                            value = float(payment.balance)
                        elif field == 'payment_mode':
                            value = payment.get_payment_mode_display()
                        elif field == 'payment_date':
                            value = payment.payment_date.strftime('%Y-%m-%d') if payment.payment_date else ''
                        elif field == 'reference_number':
                            value = payment.reference_number
                        elif field == 'status':
                            value = payment.get_status_display()
                        elif field == 'academic_year':
                            value = payment.student.academic_year.name if payment.student and payment.student.academic_year else ''
                        elif field == 'remarks':
                            value = payment.remarks
                        elif field == 'payment_number':
                            value = payment.payment_number
                        else:
                            value = getattr(payment, field, '')
                        row.append(value)
                
                for col_idx, value in enumerate(row):
                    # Apply currency format for amount columns
                    if headers[col_idx] in ['Total Amount', 'Amount Paid', 'Balance']:
                        worksheet.write(row_idx, col_idx, value, currency_format)
                    else:
                        worksheet.write(row_idx, col_idx, value)

            # Auto-adjust column widths
            for col_idx, header in enumerate(headers):
                worksheet.set_column(col_idx, col_idx, len(header) + 2)

        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return response

    def export_pdf(self, payments, filename, organization, columns):
        context = {
            "payments": payments,
            "columns": columns,
            "total_amount": payments.aggregate(total=Sum('amount'))['total'] or 0,
            "total_paid": payments.aggregate(total=Sum('amount_paid'))['total'] or 0,
            "total_balance": (payments.aggregate(total=Sum('amount'))['total'] or 0) - (payments.aggregate(total=Sum('amount_paid'))['total'] or 0),
            "total_count": payments.count(),
            "export_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": "Financial Report",
        }
        pdf_bytes = render_to_pdf("reports/export/financial_report_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)



class AcademicReportView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'reports/academic_report.html'
    permission_required = 'reports.view_academic_reports'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)

        # Initialize filter form with GET data
        filter_form = AcademicFilterForm(self.request.GET)
        filter_form.fields['student_class'].queryset = Class.objects.filter(institution=institution)
        filter_form.fields['section'].queryset = Section.objects.filter(institution=institution)
        filter_form.fields['academic_year'].queryset = AcademicYear.objects.filter(institution=institution)
        filter_form.fields['subject'].queryset = Subject.objects.filter(institution=institution)

        # Base queryset
        exam_results = ExamResult.objects.filter(
            exam_subject__exam__institution=institution
        ).select_related(
            'student__user',
            'student__current_class',
            'student__section',
            'student__academic_year',
            'exam_subject__exam',
            'exam_subject__subject'
        )

        # Apply filters if form is valid
        if filter_form.is_valid():
            data = filter_form.cleaned_data
            
            if data.get('student_class'):
                exam_results = exam_results.filter(student__current_class=data['student_class'])
            if data.get('section'):
                exam_results = exam_results.filter(student__section=data['section'])
            if data.get('academic_year'):
                exam_results = exam_results.filter(student__academic_year=data['academic_year'])
            if data.get('subject'):
                exam_results = exam_results.filter(exam_subject__subject=data['subject'])
            if data.get('exam_type'):
                exam_results = exam_results.filter(exam_subject__exam__exam_type=data['exam_type'])
            if data.get('min_marks'):
                exam_results = exam_results.filter(marks_obtained__gte=data['min_marks'])
            if data.get('max_marks'):
                exam_results = exam_results.filter(marks_obtained__lte=data['max_marks'])

        # Exam results statistics
        exam_stats = exam_results.values(
            'exam_subject__exam__name',
            'exam_subject__subject__name',
            'exam_subject__exam__exam_type'
        ).annotate(
            avg_marks=Avg('marks_obtained'),
            max_marks=Max('marks_obtained'),
            min_marks=Min('marks_obtained'),
            pass_count=Count('id', filter=Q(marks_obtained__gte=models.F('exam_subject__pass_marks'))),
            fail_count=Count('id', filter=Q(marks_obtained__lt=models.F('exam_subject__pass_marks'))),
            total_count=Count('id'),
            pass_percentage=ExpressionWrapper(
                Count('id', filter=Q(marks_obtained__gte=models.F('exam_subject__pass_marks'))) * 100.0 / Count('id'),
                output_field=models.FloatField()
            )
        ).order_by('exam_subject__exam__name', 'exam_subject__subject__name')

        # Student performance summary
        student_performance = exam_results.values(
            'student__user__first_name',
            'student__user__last_name',
            'student__admission_number',
            'student__current_class__name',
            'student__section__name'
        ).annotate(
            total_marks=Sum('marks_obtained'),
            avg_marks=Avg('marks_obtained'),
            exam_count=Count('id'),
            subjects_count=Count('exam_subject__subject', distinct=True)
        ).order_by('-avg_marks')[:20]  # Top 20 students

        # Subject-wise performance
        subject_performance = exam_results.values(
            'exam_subject__subject__name',
            'exam_subject__subject__code'
        ).annotate(
            avg_marks=Avg('marks_obtained'),
            max_marks=Max('marks_obtained'),
            min_marks=Min('marks_obtained'),
            total_students=Count('student', distinct=True),
            pass_percentage=ExpressionWrapper(
                Count('id', filter=Q(marks_obtained__gte=models.F('exam_subject__pass_marks'))) * 100.0 / Count('id'),
                output_field=models.FloatField()
            )
        ).order_by('-avg_marks')

        context.update({
            'exam_results': exam_results,
            'exam_stats': exam_stats,
            'student_performance': student_performance,
            'subject_performance': subject_performance,
            'filter_form': filter_form,
            'export_form': AcademicExportForm(),
            'academic_fields': [
                ('student', 'Student Name'),
                ('admission_number', 'Admission Number'),
                ('current_class', 'Class'),
                ('section', 'Section'),
                ('exam_name', 'Exam'),
                ('subject', 'Subject'),
                ('marks_obtained', 'Marks Obtained'),
                ('total_marks', 'Total Marks'),
                ('pass_marks', 'Pass Marks'),
                ('grade', 'Grade'),
                ('result_status', 'Result Status'),
                ('academic_year', 'Academic Year'),
            ]
        })
        
        return context

    def get(self, request, *args, **kwargs):
        format_type = request.GET.get('format', '').lower()
        if not format_type:
            return super().get(request, *args, **kwargs)

        context = self.get_context_data(**kwargs)
        records = context['exam_results']
        selected_columns = request.GET.getlist('columns')
        filename = f"academic_report_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        organization = get_user_institution(request.user)

        if format_type == 'csv':
            return self.export_csv(records, filename, selected_columns)
        elif format_type == 'excel':
            return self.export_excel(records, filename, selected_columns)
        elif format_type == 'pdf':
            return self.export_pdf(records, filename, organization, selected_columns)

        return HttpResponse("Invalid format specified", status=400)

    def export_csv(self, records, filename, columns):
        buffer = StringIO()
        writer = csv.writer(buffer)
        headers = [label for field, label in self.get_context_data()['academic_fields'] if field in columns]
        writer.writerow(headers)

        for r in records:
            row = []
            for field, label in self.get_context_data()['academic_fields']:
                if field in columns:
                    if field == 'student':
                        value = r.student.user.get_full_name()
                    elif field == 'admission_number':
                        value = r.student.admission_number
                    elif field == 'current_class':
                        value = r.student.current_class.name if r.student.current_class else ''
                    elif field == 'section':
                        value = r.student.section.name if r.student.section else ''
                    elif field == 'exam_name':
                        value = r.exam_subject.exam.name if r.exam_subject.exam else ''
                    elif field == 'subject':
                        value = r.exam_subject.subject.name if r.exam_subject.subject else ''
                    elif field == 'marks_obtained':
                        value = str(r.marks_obtained)
                    elif field == 'total_marks':
                        value = str(r.exam_subject.total_marks) if r.exam_subject else ''
                    elif field == 'pass_marks':
                        value = str(r.exam_subject.pass_marks) if r.exam_subject else ''
                    elif field == 'grade':
                        value = r.grade
                    elif field == 'result_status':
                        value = r.status
                    elif field == 'academic_year':
                        value = r.student.academic_year.name if r.student.academic_year else ''
                    else:
                        value = getattr(r, field, '')
                    row.append(value)
            writer.writerow(row)

        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response

    def export_excel(self, records, filename, columns):
        buffer = BytesIO()
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet("Academic Report")
            header_format = workbook.add_format({
                "bold": True,
                "bg_color": "#2c3e50",
                "font_color": "white",
                "border": 1,
                "align": "center",
                "valign": "vcenter"
            })

            headers = [label for field, label in self.get_context_data()['academic_fields'] if field in columns]
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            for row_idx, r in enumerate(records, start=1):
                row = []
                for field, label in self.get_context_data()['academic_fields']:
                    if field in columns:
                        if field == 'student':
                            value = r.student.user.get_full_name()
                        elif field == 'admission_number':
                            value = r.student.admission_number
                        elif field == 'current_class':
                            value = r.student.current_class.name if r.student.current_class else ''
                        elif field == 'section':
                            value = r.student.section.name if r.student.section else ''
                        elif field == 'exam_name':
                            value = r.exam_subject.exam.name if r.exam_subject.exam else ''
                        elif field == 'subject':
                            value = r.exam_subject.subject.name if r.exam_subject.subject else ''
                        elif field == 'marks_obtained':
                            value = float(r.marks_obtained)
                        elif field == 'total_marks':
                            value = float(r.exam_subject.total_marks) if r.exam_subject else 0
                        elif field == 'pass_marks':
                            value = float(r.exam_subject.pass_marks) if r.exam_subject else 0
                        elif field == 'grade':
                            value = r.grade
                        elif field == 'result_status':
                            value = r.status
                        elif field == 'academic_year':
                            value = r.student.academic_year.name if r.student.academic_year else ''
                        else:
                            value = getattr(r, field, '')
                        row.append(value)
                for col_idx, value in enumerate(row):
                    worksheet.write(row_idx, col_idx, value)

        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return response

    def export_pdf(self, records, filename, organization, columns):
        context = {
            "exam_results": records,
            "exam_stats": self.get_context_data()['exam_stats'],
            "student_performance": self.get_context_data()['student_performance'],
            "subject_performance": self.get_context_data()['subject_performance'],
            "columns": columns,
            "total_count": records.count(),
            "export_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": "Academic Report",
        }
        pdf_bytes = render_to_pdf("reports/export/academic_report_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)



class CustomReportView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = 'reports/custom_report.html'
    permission_required = 'reports.generate_custom_reports'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report_types'] = ReportType.objects.filter(institution=get_user_institution(self.request.user), is_active=True)
        return context