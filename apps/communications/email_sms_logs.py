# views.py
import csv
from io import BytesIO
from django.http import HttpResponse
from django.urls import reverse_lazy,reverse
from django.shortcuts import get_object_or_404,redirect
from django.contrib import messages
from django.db.models import Q, Sum,Count
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View,TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils import timezone
from datetime import datetime,timedelta
from io import StringIO
import xlsxwriter
from io import BytesIO
from apps.core.utils import get_user_institution
from utils.utils import render_to_pdf, export_pdf_response,qr_generate
from apps.core.utils import get_user_institution
from apps.core.mixins import StaffRequiredMixin 


from .models import Notice, Broadcast, NotificationTemplate, SMSLog, EmailLog, NoticeAudience
from .forms import NoticeForm, BroadcastForm, NotificationTemplateForm



# ---------------------- SMS Log Views ---------------------- #
class SMSLogListView( StaffRequiredMixin, ListView):
    model = SMSLog
    template_name = 'communications/sms_log/sms_log_list.html'
    context_object_name = 'sms_logs'
    paginate_by = 25

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return SMSLog.objects.filter(institution=institution)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()

        total_count = queryset.count()
        status_counts = queryset.values('status').annotate(count=Count('id'))

        context.update({
            'total_count': total_count,
            'status_counts': {item['status']: item['count'] for item in status_counts},
            'total_cost': queryset.aggregate(total_cost=Sum('cost'))['total_cost'] or 0,
        })
        return context


class SMSLogDetailView( StaffRequiredMixin, DetailView):
    model = SMSLog
    template_name = 'communications/sms_log/sms_log_detail.html'
    context_object_name = 'sms_log'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return SMSLog.objects.filter(institution=institution)


class SMSLogDeleteView( StaffRequiredMixin, DeleteView):
    model = SMSLog
    template_name = 'communications/sms_log/sms_log_confirm_delete.html'
    context_object_name = 'sms_log'
    success_url = reverse_lazy('communications:sms_log_list')

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return SMSLog.objects.filter(institution=institution)

    def delete(self, request, *args, **kwargs):
        messages.success(request, "SMS log deleted successfully!")
        return super().delete(request, *args, **kwargs)


class SMSLogExportView( StaffRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        format_type = request.GET.get('format', 'csv').lower()
        institution = get_user_institution(request.user)
        
        # Apply filters
        queryset = SMSLog.objects.filter(institution=institution)
        
        status = request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        search = request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(recipient_number__icontains=search) |
                Q(message__icontains=search)
            )
        
        queryset = queryset.select_related('template').order_by('-created_at')
        
        filename = f"sms_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if format_type == 'csv':
            return self.export_csv(queryset, filename, institution)
        elif format_type == 'excel':
            return self.export_excel(queryset, filename, institution)
        elif format_type == 'pdf':
            return self.export_pdf(queryset, filename, institution)
        else:
            return HttpResponse("Invalid format specified", status=400)
    
    def export_csv(self, queryset, filename, institution):
        buffer = StringIO()
        writer = csv.writer(buffer)
        
        # Write header
        writer.writerow([
            'Recipient Number', 'Message', 'Status', 'Template', 
            'Cost', 'Message ID', 'Scheduled For', 'Sent At', 
            'Provider Response', 'Created At'
        ])
        
        # Write data rows
        for sms in queryset:
            writer.writerow([
                sms.recipient_number,
                sms.message[:100] + '...' if len(sms.message) > 100 else sms.message,
                sms.get_status_display(),
                sms.template.name if sms.template else 'No Template',
                f"${sms.cost:.4f}" if sms.cost else 'N/A',
                sms.message_id or 'N/A',
                sms.scheduled_for.strftime('%Y-%m-%d %H:%M:%S') if sms.scheduled_for else 'Immediate',
                sms.sent_at.strftime('%Y-%m-%d %H:%M:%S') if sms.sent_at else 'Not Sent',
                str(sms.provider_response)[:50] + '...' if sms.provider_response else 'No Response',
                sms.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        # Add summary
        total_count = queryset.count()
        status_counts = queryset.values('status').annotate(count=Count('id'))
        total_cost = queryset.aggregate(total_cost=Sum('cost'))['total_cost'] or 0
        
        writer.writerow([])
        writer.writerow(['Summary Statistics'])
        writer.writerow(['Total SMS:', total_count])
        for status_count in status_counts:
            writer.writerow([f"{status_count['status'].title()} SMS:", status_count['count']])
        writer.writerow(['Total Cost:', f"${total_cost:.4f}"])
        writer.writerow(['Organization:', institution.name if institution else 'N/A'])
        writer.writerow(['Export Date:', timezone.now().strftime("%Y-%m-%d %H:%M")])
        
        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response
    
    def export_excel(self, queryset, filename, institution):
        buffer = BytesIO()
        
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet('SMS Logs')
            
            # Formats
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#3b5998',
                'font_color': 'white',
                'border': 1,
                'align': 'center'
            })
            
            date_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss'})
            currency_format = workbook.add_format({'num_format': '$#,##0.0000'})
            
            # Headers
            headers = [
                'Recipient Number', 'Message', 'Status', 'Template', 
                'Cost', 'Message ID', 'Scheduled For', 'Sent At', 'Created At'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
            
            # Data
            for row_idx, sms in enumerate(queryset, start=1):
                worksheet.write(row_idx, 0, sms.recipient_number)
                worksheet.write(row_idx, 1, sms.message)
                worksheet.write(row_idx, 2, sms.get_status_display())
                worksheet.write(row_idx, 3, sms.template.name if sms.template else 'No Template')
                worksheet.write(row_idx, 4, float(sms.cost) if sms.cost else 0, currency_format)
                worksheet.write(row_idx, 5, sms.message_id or 'N/A')
                worksheet.write(row_idx, 6, sms.scheduled_for, date_format if sms.scheduled_for else None)
                worksheet.write(row_idx, 7, sms.sent_at, date_format if sms.sent_at else None)
                worksheet.write(row_idx, 8, sms.created_at, date_format)
            
            # Adjust columns
            worksheet.set_column('A:A', 20)  # Recipient Number
            worksheet.set_column('B:B', 50)  # Message
            worksheet.set_column('C:C', 15)  # Status
            worksheet.set_column('D:D', 25)  # Template
            worksheet.set_column('E:E', 12)  # Cost
            worksheet.set_column('F:F', 30)  # Message ID
            worksheet.set_column('G:G', 20)  # Scheduled For
            worksheet.set_column('H:H', 20)  # Sent At
            worksheet.set_column('I:I', 20)  # Created At
            
            # Summary
            total_count = queryset.count()
            status_counts = queryset.values('status').annotate(count=Count('id'))
            total_cost = queryset.aggregate(total_cost=Sum('cost'))['total_cost'] or 0
            
            summary_row = len(queryset) + 3
            worksheet.write(summary_row, 0, 'Summary Statistics', header_format)
            worksheet.merge_range(summary_row, 0, summary_row, 1, 'Summary Statistics', header_format)
            
            worksheet.write(summary_row + 1, 0, 'Total SMS:')
            worksheet.write(summary_row + 1, 1, total_count)
            
            row_offset = summary_row + 2
            for status_count in status_counts:
                worksheet.write(row_offset, 0, f"{status_count['status'].title()} SMS:")
                worksheet.write(row_offset, 1, status_count['count'])
                row_offset += 1
            
            worksheet.write(row_offset, 0, 'Total Cost:')
            worksheet.write(row_offset, 1, float(total_cost), currency_format)
            
            worksheet.write(row_offset + 1, 0, 'Organization:')
            worksheet.write(row_offset + 1, 1, institution.name if institution else 'N/A')
            
            worksheet.write(row_offset + 2, 0, 'Export Date:')
            worksheet.write(row_offset + 2, 1, timezone.now().strftime("%Y-%m-%d %H:%M"))
        
        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return response
    
    def export_pdf(self, queryset, filename, institution):
        rows = [
            {
                'recipient_number': sms.recipient_number,
                'message': sms.message,
                'status': sms.get_status_display(),
                'status_raw': sms.status,
                'template': sms.template.name if sms.template else 'No Template',
                'cost': f"${sms.cost:.4f}" if sms.cost else 'N/A',
                'message_id': sms.message_id or 'N/A',
                'scheduled_for': sms.scheduled_for.strftime('%Y-%m-%d %H:%M:%S') if sms.scheduled_for else 'Immediate',
                'sent_at': sms.sent_at.strftime('%Y-%m-%d %H:%M:%S') if sms.sent_at else 'Not Sent',
                'created_at': sms.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'provider_response': str(sms.provider_response) if sms.provider_response else 'No Response'
            }
            for sms in queryset
        ]

        status_counts = list(queryset.values('status').annotate(count=Count('id')))
        total_cost = queryset.aggregate(total_cost=Sum('cost'))['total_cost'] or 0

        context = {
            "sms_logs": rows,
            "total_count": queryset.count(),
            "status_counts": status_counts,
            "total_cost": total_cost,
            "organization": institution,
            "export_date": timezone.now(),
            "title": "SMS Logs Export",
        }

        pdf_bytes = render_to_pdf("communications/export/sms_logs_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=400)


# ---------------------- Email Log Views ---------------------- #
class EmailLogListView( StaffRequiredMixin, ListView):
    model = EmailLog
    template_name = 'communications/email_log/email_log_list.html'
    context_object_name = 'email_logs'
    paginate_by = 25

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        queryset = EmailLog.objects.filter(institution=institution)
        
        # Filter by status
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by date range
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        # Search by recipient email or subject
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(recipient_email__icontains=search) |
                Q(subject__icontains=search) |
                Q(message_id__icontains=search)
            )
        
        return queryset.select_related('template').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        
        # Get statistics
        queryset = self.get_queryset()
        total_count = queryset.count()
        status_counts = queryset.values('status').annotate(count=Count('id'))
        
        # Engagement metrics
        opened_count = queryset.filter(opened_at__isnull=False).count()
        clicked_count = queryset.filter(clicked_at__isnull=False).count()
        
        context.update({
            'total_count': total_count,
            'status_counts': {item['status']: item['count'] for item in status_counts},
            'opened_count': opened_count,
            'clicked_count': clicked_count,
            'open_rate': (opened_count / total_count * 100) if total_count > 0 else 0,
            'click_rate': (clicked_count / total_count * 100) if total_count > 0 else 0,
        })
        return context


class EmailLogDetailView( StaffRequiredMixin, DetailView):
    model = EmailLog
    template_name = 'communications/email_log/email_log_detail.html'
    context_object_name = 'email_log'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return EmailLog.objects.filter(institution=institution)


class EmailLogDeleteView( StaffRequiredMixin, DeleteView):
    model = EmailLog
    template_name = 'communications/email_log/email_log_confirm_delete.html'
    context_object_name = 'email_log'
    success_url = reverse_lazy('communications:email_log_list')

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return EmailLog.objects.filter(institution=institution)

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Email log deleted successfully!")
        return super().delete(request, *args, **kwargs)


class EmailLogExportView( StaffRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        format_type = request.GET.get('format', 'csv').lower()
        institution = get_user_institution(request.user)
        
        # Apply filters
        queryset = EmailLog.objects.filter(institution=institution)
        
        status = request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        search = request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(recipient_email__icontains=search) |
                Q(subject__icontains=search)
            )
        
        queryset = queryset.select_related('template').order_by('-created_at')
        
        filename = f"email_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        if format_type == 'csv':
            return self.export_csv(queryset, filename, institution)
        elif format_type == 'excel':
            return self.export_excel(queryset, filename, institution)
        elif format_type == 'pdf':
            return self.export_pdf(queryset, filename, institution)
        else:
            return HttpResponse("Invalid format specified", status=400)
    
    def export_csv(self, queryset, filename, institution):
        buffer = StringIO()
        writer = csv.writer(buffer)
        
        # Write header
        writer.writerow([
            'Recipient Email', 'Subject', 'Status', 'Template', 
            'Message ID', 'Scheduled For', 'Sent At', 'Opened At', 
            'Clicked At', 'Created At'
        ])
        
        # Write data rows
        for email in queryset:
            writer.writerow([
                email.recipient_email,
                email.subject,
                email.get_status_display(),
                email.template.name if email.template else 'No Template',
                email.message_id or 'N/A',
                email.scheduled_for.strftime('%Y-%m-%d %H:%M:%S') if email.scheduled_for else 'Immediate',
                email.sent_at.strftime('%Y-%m-%d %H:%M:%S') if email.sent_at else 'Not Sent',
                email.opened_at.strftime('%Y-%m-%d %H:%M:%S') if email.opened_at else 'Not Opened',
                email.clicked_at.strftime('%Y-%m-%d %H:%M:%S') if email.clicked_at else 'Not Clicked',
                email.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        # Add summary
        total_count = queryset.count()
        status_counts = queryset.values('status').annotate(count=Count('id'))
        opened_count = queryset.filter(opened_at__isnull=False).count()
        clicked_count = queryset.filter(clicked_at__isnull=False).count()
        
        writer.writerow([])
        writer.writerow(['Summary Statistics'])
        writer.writerow(['Total Emails:', total_count])
        for status_count in status_counts:
            writer.writerow([f"{status_count['status'].title()} Emails:", status_count['count']])
        writer.writerow(['Opened Emails:', opened_count])
        writer.writerow(['Clicked Emails:', clicked_count])
        writer.writerow(['Open Rate:', f"{(opened_count/total_count*100):.1f}%" if total_count > 0 else "0%"])
        writer.writerow(['Click Rate:', f"{(clicked_count/total_count*100):.1f}%" if total_count > 0 else "0%"])
        writer.writerow(['Organization:', institution.name if institution else 'N/A'])
        writer.writerow(['Export Date:', timezone.now().strftime("%Y-%m-%d %H:%M")])
        
        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response
    
    def export_excel(self, queryset, filename, institution):
        buffer = BytesIO()
        
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet('Email Logs')
            
            # Formats
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#3b5998',
                'font_color': 'white',
                'border': 1,
                'align': 'center'
            })
            
            date_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss'})
            
            # Headers
            headers = [
                'Recipient Email', 'Subject', 'Status', 'Template', 
                'Message ID', 'Scheduled For', 'Sent At', 'Opened At', 'Clicked At', 'Created At'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
            
            # Data
            for row_idx, email in enumerate(queryset, start=1):
                worksheet.write(row_idx, 0, email.recipient_email)
                worksheet.write(row_idx, 1, email.subject)
                worksheet.write(row_idx, 2, email.get_status_display())
                worksheet.write(row_idx, 3, email.template.name if email.template else 'No Template')
                worksheet.write(row_idx, 4, email.message_id or 'N/A')
                worksheet.write(row_idx, 5, email.scheduled_for, date_format if email.scheduled_for else None)
                worksheet.write(row_idx, 6, email.sent_at, date_format if email.sent_at else None)
                worksheet.write(row_idx, 7, email.opened_at, date_format if email.opened_at else None)
                worksheet.write(row_idx, 8, email.clicked_at, date_format if email.clicked_at else None)
                worksheet.write(row_idx, 9, email.created_at, date_format)
            
            # Adjust columns
            worksheet.set_column('A:A', 25)  # Recipient Email
            worksheet.set_column('B:B', 40)  # Subject
            worksheet.set_column('C:C', 15)  # Status
            worksheet.set_column('D:D', 25)  # Template
            worksheet.set_column('E:E', 30)  # Message ID
            worksheet.set_column('F:F', 20)  # Scheduled For
            worksheet.set_column('G:G', 20)  # Sent At
            worksheet.set_column('H:H', 20)  # Opened At
            worksheet.set_column('I:I', 20)  # Clicked At
            worksheet.set_column('J:J', 20)  # Created At
            
            # Summary
            total_count = queryset.count()
            status_counts = queryset.values('status').annotate(count=Count('id'))
            opened_count = queryset.filter(opened_at__isnull=False).count()
            clicked_count = queryset.filter(clicked_at__isnull=False).count()
            
            summary_row = len(queryset) + 3
            worksheet.write(summary_row, 0, 'Summary Statistics', header_format)
            worksheet.merge_range(summary_row, 0, summary_row, 1, 'Summary Statistics', header_format)
            
            worksheet.write(summary_row + 1, 0, 'Total Emails:')
            worksheet.write(summary_row + 1, 1, total_count)
            
            row_offset = summary_row + 2
            for status_count in status_counts:
                worksheet.write(row_offset, 0, f"{status_count['status'].title()} Emails:")
                worksheet.write(row_offset, 1, status_count['count'])
                row_offset += 1
            
            worksheet.write(row_offset, 0, 'Opened Emails:')
            worksheet.write(row_offset, 1, opened_count)
            
            worksheet.write(row_offset + 1, 0, 'Clicked Emails:')
            worksheet.write(row_offset + 1, 1, clicked_count)
            
            worksheet.write(row_offset + 2, 0, 'Organization:')
            worksheet.write(row_offset + 2, 1, institution.name if institution else 'N/A')
            
            worksheet.write(row_offset + 3, 0, 'Export Date:')
            worksheet.write(row_offset + 3, 1, timezone.now().strftime("%Y-%m-%d %H:%M"))
        
        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return response
    
    def export_pdf(self, queryset, filename, institution):
        # Prepare data for PDF
        rows = []
        for email in queryset:
            rows.append({
                'recipient_email': email.recipient_email,
                'subject': email.subject,
                'message_preview': email.message[:100] + '...' if len(email.message) > 100 else email.message,
                'status': email.get_status_display(),
                'status_raw': email.status,
                'template': email.template.name if email.template else 'No Template',
                'message_id': email.message_id or 'N/A',
                'scheduled_for': email.scheduled_for.strftime('%Y-%m-%d %H:%M:%S') if email.scheduled_for else 'Immediate',
                'sent_at': email.sent_at.strftime('%Y-%m-%d %H:%M:%S') if email.sent_at else 'Not Sent',
                'opened_at': email.opened_at.strftime('%Y-%m-%d %H:%M:%S') if email.opened_at else 'Not Opened',
                'clicked_at': email.clicked_at.strftime('%Y-%m-%d %H:%M:%S') if email.clicked_at else 'Not Clicked',
                'created_at': email.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        # Statistics
        total_count = queryset.count()
        status_counts = queryset.values('status').annotate(count=Count('id'))
        opened_count = queryset.filter(opened_at__isnull=False).count()
        clicked_count = queryset.filter(clicked_at__isnull=False).count()
        
        context = {
            "email_logs": rows,
            "total_count": total_count,
            "status_counts": list(status_counts),
            "opened_count": opened_count,
            "clicked_count": clicked_count,
            "open_rate": (opened_count / total_count * 100) if total_count > 0 else 0,
            "click_rate": (clicked_count / total_count * 100) if total_count > 0 else 0,
            "organization": institution,
            "export_date": timezone.now(),
            "title": "Email Logs Export",
        }
        
        pdf_bytes = render_to_pdf("communications/export/email_logs_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=400)