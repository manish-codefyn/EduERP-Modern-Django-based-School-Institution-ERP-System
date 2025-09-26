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

class CommunicationsDashboardView( StaffRequiredMixin, TemplateView):
    template_name = 'communications/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        
        if not institution:
            return context
        
        # Date ranges for analytics
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Notices Statistics
        notices = Notice.objects.filter(institution=institution)
        total_notices = notices.count()
        published_notices = notices.filter(is_published=True).count()
        draft_notices = notices.filter(is_published=False).count()
        urgent_notices = notices.filter(priority='urgent').count()

        # Calculate percentages safely
        published_percentage = (published_notices / total_notices * 100) if total_notices > 0 else 0
        draft_percentage = (draft_notices / total_notices * 100) if total_notices > 0 else 0
        urgent_percentage = (urgent_notices / total_notices * 100) if total_notices > 0 else 0

        

        # Notices by audience
        notices_by_audience = list(notices.values('audience').annotate(
            count=Count('id')
        ).order_by('-count'))
        
        # Notices by priority
        notices_by_priority = list(notices.values('priority').annotate(
            count=Count('id')
        ).order_by('-count'))
        
        # Recent notices (last 7 days)
        recent_notices = notices.filter(
            created_at__date__gte=week_ago
        ).order_by('-created_at')[:5]
        
        # Broadcast Statistics
        broadcasts = Broadcast.objects.filter(institution=institution)
        total_broadcasts = broadcasts.count()
        completed_broadcasts = broadcasts.filter(status='completed').count()
        scheduled_broadcasts = broadcasts.filter(status='scheduled').count()
        failed_broadcasts = broadcasts.filter(status='failed').count()
        
        # Broadcast success rates
        if total_broadcasts > 0:
            broadcast_success_rate = (completed_broadcasts / total_broadcasts) * 100
        else:
            broadcast_success_rate = 0
        
        # SMS Statistics
        sms_logs = SMSLog.objects.filter(institution=institution)
        total_sms = sms_logs.count()
        sent_sms = sms_logs.filter(status='sent').count()
        delivered_sms = sms_logs.filter(status='delivered').count()
        failed_sms = sms_logs.filter(status='failed').count()
        
        # Email Statistics
        email_logs = EmailLog.objects.filter(institution=institution)
        total_emails = email_logs.count()
        sent_emails = email_logs.filter(status='sent').count()
        delivered_emails = email_logs.filter(status='delivered').count()
        failed_emails = email_logs.filter(status='failed').count()
        
        # Template Statistics
        templates = NotificationTemplate.objects.filter(institution=institution)
        total_templates = templates.count()
        active_templates = templates.filter(is_active=True).count()
        
        # Templates by type
        templates_by_type = list(templates.values('template_type').annotate(
            count=Count('id')
        ).order_by('-count'))
        
        # Audience engagement for notices
        notice_audience_stats = NoticeAudience.objects.filter(
            notice__institution=institution
        ).aggregate(
            total=Count('id'),
            read_count=Count('id', filter=Q(read=True)),
            unread_count=Count('id', filter=Q(read=False))
        )

        # Make sure to use the exact keys from the aggregate
        total = notice_audience_stats['total']
        read_count = notice_audience_stats['read_count']
        unread_count = notice_audience_stats['unread_count']

        if total > 0:
            read_percentage = (read_count / total) * 100
            unread_percentage = (unread_count / total) * 100
        else:
            read_percentage = 0
            unread_percentage = 0
        

        
        # Monthly activity data for charts
        monthly_data = self.get_monthly_activity_data(institution)
        
        context.update({
            # Notices data
            'total_notices': total_notices,
            'published_notices': published_notices,
            'draft_notices': draft_notices,
            'urgent_notices': urgent_notices,
            'notices_by_audience': notices_by_audience,
            'notices_by_priority': notices_by_priority,
            'recent_notices': recent_notices,
            'published_percentage': round(published_percentage, 1),
            'draft_percentage': round(draft_percentage, 1),
            'urgent_percentage': round(urgent_percentage, 1),
            # Broadcasts data
            'total_broadcasts': total_broadcasts,
            'completed_broadcasts': completed_broadcasts,
            'scheduled_broadcasts': scheduled_broadcasts,
            'failed_broadcasts': failed_broadcasts,
            'broadcast_success_rate': round(broadcast_success_rate, 1),
            
            # SMS data
            'total_sms': total_sms,
            'sent_sms': sent_sms,
            'delivered_sms': delivered_sms,
            'failed_sms': failed_sms,
            'sms_success_rate': round((delivered_sms / total_sms * 100) if total_sms > 0 else 0, 1),
            
            # Email data
            'total_emails': total_emails,
            'sent_emails': sent_emails,
            'delivered_emails': delivered_emails,
            'failed_emails': failed_emails,
            'email_success_rate': round((delivered_emails / total_emails * 100) if total_emails > 0 else 0, 1),
            
            # Templates data
            'total_templates': total_templates,
            'active_templates': active_templates,
            'templates_by_type': templates_by_type,
            
            # Audience engagement
            'total_audience': notice_audience_stats['total'],
            'read_audience': notice_audience_stats['read_count'],
            'unread_audience': notice_audience_stats['unread_count'],
            'read_percentage': round(read_percentage, 1),

                        
            # Chart data
            'monthly_data': monthly_data,
            'chart_labels': monthly_data['labels'],
            'chart_notices': monthly_data['notices'],
            'chart_broadcasts': monthly_data['broadcasts'],
            'chart_sms': monthly_data['sms'],
            'chart_emails': monthly_data['emails'],
            
            # Date ranges
            'today': today,
            'week_ago': week_ago,
            'month_ago': month_ago,
        })
        
        return context
    
    def get_monthly_activity_data(self, institution):
        """Generate monthly activity data for charts"""
        today = timezone.now().date()
        months = []
        notices_data = []
        broadcasts_data = []
        sms_data = []
        emails_data = []
        
        # Get data for last 6 months
        for i in range(5, -1, -1):
            month_start = today.replace(day=1) - timedelta(days=30*i)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            
            months.append(month_start.strftime('%b %Y'))
            
            # Notices count for month
            notices_count = Notice.objects.filter(
                institution=institution,
                created_at__date__range=[month_start, month_end]
            ).count()
            notices_data.append(notices_count)
            
            # Broadcasts count for month
            broadcasts_count = Broadcast.objects.filter(
                institution=institution,
                created_at__date__range=[month_start, month_end]
            ).count()
            broadcasts_data.append(broadcasts_count)
            
            # SMS count for month
            sms_count = SMSLog.objects.filter(
                institution=institution,
                created_at__date__range=[month_start, month_end]
            ).count()
            sms_data.append(sms_count)
            
            # Emails count for month
            email_count = EmailLog.objects.filter(
                institution=institution,
                created_at__date__range=[month_start, month_end]
            ).count()
            emails_data.append(email_count)
        
        return {
            'labels': months,
            'notices': notices_data,
            'broadcasts': broadcasts_data,
            'sms': sms_data,
            'emails': emails_data
        }
    
# ---------------------- Notice Views ---------------------- #
class NoticeListView( StaffRequiredMixin, ListView):
    model = Notice
    template_name = 'communications/notice/notice_list.html'
    context_object_name = 'notices'
    paginate_by = 20

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        queryset = Notice.objects.filter(institution=institution)

        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(content__icontains=search))

        # Filters
        audience = self.request.GET.get('audience')
        if audience:
            queryset = queryset.filter(audience=audience)

        priority = self.request.GET.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)

        status = self.request.GET.get('status')
        if status == 'published':
            queryset = queryset.filter(is_published=True)
        elif status == 'draft':
            queryset = queryset.filter(is_published=False)

        return queryset.order_by('-publish_date', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        context['total_notices'] = queryset.count()
        context['published_notices'] = queryset.filter(is_published=True).count()
        context['draft_notices'] = queryset.filter(is_published=False).count()
        return context


class NoticeCreateView( StaffRequiredMixin, CreateView):
    model = Notice
    form_class = NoticeForm
    template_name = 'communications/notice/notice_form.html'
    success_url = reverse_lazy('communications:notice_list')

    def form_valid(self, form):
        form.instance.institution = get_user_institution(self.request.user)
        form.instance.created_by = self.request.user
        messages.success(self.request, "Notice created successfully!")
        return super().form_valid(form)


class NoticeUpdateView( StaffRequiredMixin, UpdateView):
    model = Notice
    form_class = NoticeForm
    template_name = 'communications/notice/notice_form.html'
    success_url = reverse_lazy('communications:notice_list')

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Notice.objects.filter(institution=institution)

    def form_valid(self, form):
        messages.success(self.request, "Notice updated successfully!")
        return super().form_valid(form)


class NoticeDetailView( StaffRequiredMixin, DetailView):
    model = Notice
    template_name = 'communications/notice/notice_detail.html'
    context_object_name = 'notice'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Notice.objects.filter(institution=institution)


class NoticeDeleteView( StaffRequiredMixin, DeleteView):
    model = Notice
    template_name = 'communications/notice/notice_confirm_delete.html'
    success_url = reverse_lazy('communications:notice_list')

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return Notice.objects.filter(institution=institution)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Notice deleted successfully!")
        return super().delete(request, *args, **kwargs)


# ---------------------- Broadcast Views ---------------------- #
class BroadcastListView( StaffRequiredMixin, ListView):
    model = Broadcast
    template_name = 'communications/broadcast/broadcast_list.html'
    context_object_name = 'broadcasts'
    paginate_by = 20

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        queryset = Broadcast.objects.filter(institution=institution)

        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(message__icontains=search))

        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)

        return queryset.order_by('-created_at')


class BroadcastCreateView( StaffRequiredMixin, CreateView):
    model = Broadcast
    form_class = BroadcastForm
    template_name = 'communications/broadcast/broadcast_form.html'
    success_url = reverse_lazy('communications:broadcast_list')

    def form_valid(self, form):
        form.instance.institution = get_user_institution(self.request.user)
        form.instance.created_by = self.request.user
        messages.success(self.request, "Broadcast created successfully!")
        return super().form_valid(form)
    
    
class BroadcastUpdateView( StaffRequiredMixin, UpdateView):
    model = Broadcast
    form_class = BroadcastForm
    template_name = 'communications/broadcast/broadcast_form.html'
    context_object_name = 'broadcast'
    
    def get_queryset(self):
        # Restrict to broadcasts belonging to user's institution
        return Broadcast.objects.filter(institution=get_user_institution(self.request.user))
    
    def form_valid(self, form):
        # Ensure institution and created_by are not changed accidentally
        form.instance.institution = get_user_institution(self.request.user)
        form.instance.created_by = self.request.user
        messages.success(self.request, "Broadcast updated successfully!")
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse_lazy('communications:broadcast_detail', kwargs={'pk': self.object.pk})

class BroadcastDetailView( StaffRequiredMixin, DetailView):
    model = Broadcast
    template_name = 'communications/broadcast/broadcast_detail.html'
    context_object_name = 'broadcast'
    
    def get_queryset(self):
        return Broadcast.objects.filter(institution=get_user_institution(self.request.user))
    
class BroadcastDeleteView( StaffRequiredMixin, DeleteView):
    model = Broadcast
    template_name = 'communications/broadcast/broadcast_confirm_delete.html'
    context_object_name = 'broadcast'
    success_url = reverse_lazy('communications:broadcast_list')  # redirect after delete

    def get_queryset(self):
        # Ensure user can only delete broadcasts from their institution
        return Broadcast.objects.filter(institution=get_user_institution(self.request.user))

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Broadcast deleted successfully!")
        return super().delete(request, *args, **kwargs)

# ---------------------- Notification Template Views ---------------------- #
class NotificationTemplateListView( StaffRequiredMixin, ListView):
    model = NotificationTemplate
    template_name = 'communications/templates/template_list.html'
    context_object_name = 'templates'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return NotificationTemplate.objects.filter(institution=institution).order_by('name')


class NotificationTemplateCreateView( StaffRequiredMixin, CreateView):
    model = NotificationTemplate
    form_class = NotificationTemplateForm
    template_name = 'communications/templates/template_form.html'
    success_url = reverse_lazy('communications:template_list')

    def form_valid(self, form):
        form.instance.institution = get_user_institution(self.request.user)
        messages.success(self.request, "Notification template created successfully!")
        return super().form_valid(form)

    def form_invalid(self, form):
        print("Form errors:", form.errors)  # <--- See why it's invalid
        messages.error(self.request, "Please correct the errors below.")
        return super().form_invalid(form)
    
    
class NotificationTemplateUpdateView( StaffRequiredMixin, UpdateView):
    model = NotificationTemplate
    form_class = NotificationTemplateForm
    template_name = 'communications/templates/template_form.html'
    context_object_name = 'template'
    success_url = reverse_lazy('communications:template_list')

    def get_queryset(self):
        # Ensure user can only edit templates belonging to their institution
        return NotificationTemplate.objects.filter(institution=get_user_institution(self.request.user))

    def form_valid(self, form):
        messages.success(self.request, "Notification template updated successfully!")
        return super().form_valid(form)

class NotificationTemplateDetailView( StaffRequiredMixin, DetailView):
    model = NotificationTemplate
    template_name = 'communications/templates/template_detail.html'
    context_object_name = 'template'
    
    def get_queryset(self):
        return NotificationTemplate.objects.filter(institution=get_user_institution(self.request.user))


class NotificationTemplateDeleteView( StaffRequiredMixin, DeleteView):
    model = NotificationTemplate
    template_name = 'communications/templates/template_confirm_delete.html'
    context_object_name = 'template'
    success_url = reverse_lazy('communications:template_list')  # redirect after delete

    def get_queryset(self):
        """Limit deletion to templates of the user's institution"""
        return NotificationTemplate.objects.filter(institution=get_user_institution(self.request.user))

    def delete(self, request, *args, **kwargs):
        """Add success message on deletion"""
        response = super().delete(request, *args, **kwargs)
        messages.success(request, "Notification template deleted successfully!")
        return response


class NotificationTemplateDeleteView( StaffRequiredMixin, DeleteView):
    model = NotificationTemplate
    template_name = 'communications/templates/template_confirm_delete.html'
    context_object_name = 'template'
    success_url = reverse_lazy('communications:template_list')

    def get_queryset(self):
        # Only allow deleting templates from user's institution
        return NotificationTemplate.objects.filter(institution=get_user_institution(self.request.user))

class NoticeExportView( StaffRequiredMixin, ListView):
    model = Notice
    context_object_name = 'notices'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        institution = get_user_institution(self.request.user)
        
        if institution:
            queryset = queryset.filter(institution=institution)
        
        # Apply filters from request
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) | 
                Q(content__icontains=search)
            )
        
        audience = self.request.GET.get('audience')
        if audience:
            queryset = queryset.filter(audience=audience)
        
        priority = self.request.GET.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        status = self.request.GET.get('status')
        if status == 'published':
            queryset = queryset.filter(is_published=True)
        elif status == 'draft':
            queryset = queryset.filter(is_published=False)
        
        return queryset.order_by('-publish_date', '-created_at')
    
    def get(self, request, *args, **kwargs):
        format_type = request.GET.get('format', 'csv').lower()
        queryset = self.get_queryset()
        
        # Build filename
        filename = f"notices_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Build data rows
        rows = []
        for notice in queryset:
            # Get audience statistics
            audience_details = NoticeAudience.objects.filter(notice=notice)
            total_audience = audience_details.count()
            read_count = audience_details.filter(read=True).count()
            
            rows.append({
                "title": notice.title,
                "content": notice.content,
                "priority": notice.get_priority_display(),
                "audience": notice.get_audience_display(),
                "is_published": "Yes" if notice.is_published else "No",
                "publish_date": notice.publish_date.strftime('%Y-%m-%d %H:%M') if notice.publish_date else 'Not Published',
                "expiry_date": notice.expiry_date.strftime('%Y-%m-%d %H:%M') if notice.expiry_date else 'No Expiry',
                "attachment": notice.attachment.name if notice.attachment else 'No Attachment',
                "created_by": notice.created_by.get_full_name(),
                "created_at": notice.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                "updated_at": notice.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
                "total_audience": total_audience,
                "read_count": read_count,
                "read_percentage": f"{(read_count/total_audience*100):.1f}%" if total_audience > 0 else "0%",
                "audience_type": notice.audience,
                "priority_level": notice.priority,
            })

        # Get organization info
        organization = get_user_institution(request.user)
        
        if format_type == 'csv':
            return self.export_csv(rows, filename, organization)
        elif format_type == 'excel':
            return self.export_excel(rows, filename, organization)
        elif format_type == 'pdf':
            return self.export_pdf(rows, filename, organization, queryset.count())
        else:
            return HttpResponse("Invalid format specified", status=400)
    
    def export_csv(self, rows, filename, organization):
        """Export notices to CSV format"""
        buffer = StringIO()
        writer = csv.writer(buffer)
        
        # Write header
        writer.writerow([
            'Title', 'Content Preview', 'Priority', 'Audience', 'Status', 
            'Publish Date', 'Expiry Date', 'Attachment', 'Created By', 
            'Total Audience', 'Read Count', 'Read Percentage', 'Created At'
        ])
        
        # Write data rows
        for row in rows:
            writer.writerow([
                row['title'],
                row['content'][:100] + '...' if len(row['content']) > 100 else row['content'],
                row['priority'],
                row['audience'],
                row['is_published'],
                row['publish_date'],
                row['expiry_date'],
                row['attachment'],
                row['created_by'],
                row['total_audience'],
                row['read_count'],
                row['read_percentage'],
                row['created_at']
            ])
        
        # Add summary row
        writer.writerow([])
        writer.writerow(['Total Notices:', len(rows)])
        writer.writerow(['Published:', len([r for r in rows if r['is_published'] == 'Yes'])])
        writer.writerow(['Drafts:', len([r for r in rows if r['is_published'] == 'No'])])
        writer.writerow(['Organization:', organization.name if organization else 'N/A'])
        writer.writerow(['Export Date:', timezone.now().strftime("%Y-%m-%d %H:%M")])
        
        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response
    
    def export_excel(self, rows, filename, organization):
        """Export notices to Excel format"""
        buffer = BytesIO()
        
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet('Notices List')
            
            # Add formats
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#3b5998',
                'font_color': 'white',
                'border': 1,
                'align': 'center',
                'valign': 'vcenter'
            })
            
            date_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss'})
            center_format = workbook.add_format({'align': 'center'})
            wrap_format = workbook.add_format({'text_wrap': True})
            
            # Write headers
            headers = [
                'Title', 'Content Preview', 'Priority', 'Audience', 'Status', 
                'Publish Date', 'Expiry Date', 'Attachment', 'Created By', 
                'Total Audience', 'Read Count', 'Read Percentage', 'Created At'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
            
            # Write data
            for row_idx, row_data in enumerate(rows, start=1):
                worksheet.write(row_idx, 0, row_data['title'])
                worksheet.write(row_idx, 1, row_data['content'][:500])  # Limit content length
                worksheet.write(row_idx, 2, row_data['priority'])
                worksheet.write(row_idx, 3, row_data['audience'])
                worksheet.write(row_idx, 4, row_data['is_published'], center_format)
                worksheet.write(row_idx, 5, row_data['publish_date'])
                worksheet.write(row_idx, 6, row_data['expiry_date'])
                worksheet.write(row_idx, 7, row_data['attachment'])
                worksheet.write(row_idx, 8, row_data['created_by'])
                worksheet.write(row_idx, 9, row_data['total_audience'], center_format)
                worksheet.write(row_idx, 10, row_data['read_count'], center_format)
                worksheet.write(row_idx, 11, row_data['read_percentage'], center_format)
                worksheet.write(row_idx, 12, row_data['created_at'], date_format)
            
            # Adjust column widths
            worksheet.set_column('A:A', 30)  # Title
            worksheet.set_column('B:B', 50)  # Content Preview
            worksheet.set_column('C:C', 15)  # Priority
            worksheet.set_column('D:D', 15)  # Audience
            worksheet.set_column('E:E', 12)  # Status
            worksheet.set_column('F:F', 20)  # Publish Date
            worksheet.set_column('G:G', 20)  # Expiry Date
            worksheet.set_column('H:H', 25)  # Attachment
            worksheet.set_column('I:I', 25)  # Created By
            worksheet.set_column('J:J', 15)  # Total Audience
            worksheet.set_column('K:K', 12)  # Read Count
            worksheet.set_column('L:L', 15)  # Read Percentage
            worksheet.set_column('M:M', 20)  # Created At
            
            # Add summary
            summary_row = len(rows) + 2
            published_count = len([r for r in rows if r['is_published'] == 'Yes'])
            draft_count = len([r for r in rows if r['is_published'] == 'No'])
            
            worksheet.write(summary_row, 0, 'Total Notices:')
            worksheet.write(summary_row, 1, len(rows))
            
            worksheet.write(summary_row + 1, 0, 'Published:')
            worksheet.write(summary_row + 1, 1, published_count)
            
            worksheet.write(summary_row + 2, 0, 'Drafts:')
            worksheet.write(summary_row + 2, 1, draft_count)
            
            worksheet.write(summary_row + 3, 0, 'Organization:')
            worksheet.write(summary_row + 3, 1, organization.name if organization else 'N/A')
            
            worksheet.write(summary_row + 4, 0, 'Export Date:')
            worksheet.write(summary_row + 4, 1, timezone.now().strftime("%Y-%m-%d %H:%M"))
        
        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return response
    
    def export_pdf(self, rows, filename, organization, total_count):
        """Export notices to PDF format"""
        context = {
            "notices": rows,
            "total_count": total_count,
            "published_count": len([r for r in rows if r['is_published'] == 'Yes']),
            "draft_count": len([r for r in rows if r['is_published'] == 'No']),
            "export_date": timezone.now(),
            "organization": organization,
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": "Notices List Export",
            "columns": [
                {'name': 'Title', 'width': '25%'},
                {'name': 'Priority', 'width': '10%'},
                {'name': 'Audience', 'width': '15%'},
                {'name': 'Status', 'width': '10%'},
                {'name': 'Publish Date', 'width': '15%'},
                {'name': 'Read Rate', 'width': '10%'},
                {'name': 'Created By', 'width': '15%'},
            ]
        }
        
        pdf_bytes = render_to_pdf("communications/export/notices_list_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)


class NoticeDetailExportView( StaffRequiredMixin, View):
    """Export a single notice's details in CSV, Excel, or PDF"""

    def get(self, request, pk, *args, **kwargs):
        notice = get_object_or_404(Notice, pk=pk)
        format_type = request.GET.get('format', 'csv').lower()

        # Get audience details
        audience_details = NoticeAudience.objects.filter(notice=notice)
        total_audience = audience_details.count()
        read_count = audience_details.filter(read=True).count()
        unread_count = total_audience - read_count

        # Prepare data row with all fields
        row = {
            "title": notice.title,
            "content": notice.content,
            "priority": notice.get_priority_display(),
            "priority_level": notice.priority,
            "audience": notice.get_audience_display(),
            "audience_type": notice.audience,
            "is_published": "Yes" if notice.is_published else "No",
            "publish_date": notice.publish_date.strftime('%Y-%m-%d %H:%M:%S') if notice.publish_date else 'Not Published',
            "expiry_date": notice.expiry_date.strftime('%Y-%m-%d %H:%M:%S') if notice.expiry_date else 'No Expiry',
            "attachment": notice.attachment.name if notice.attachment else 'No Attachment',
            "attachment_url": notice.attachment.url if notice.attachment else '',
            "attachment_size": notice.attachment.size if notice.attachment else 0,
            "created_by": notice.created_by.get_full_name(),
            "created_by_email": notice.created_by.email,
            "created_at": notice.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            "updated_at": notice.updated_at.strftime('%Y-%m-%d %H:%M:%S'),
            
            # Audience statistics
            "total_audience": total_audience,
            "read_count": read_count,
            "unread_count": unread_count,
            "read_percentage": f"{(read_count/total_audience*100):.1f}%" if total_audience > 0 else "0%",
            
            # Institution info
            "institution": notice.institution.name,
            "institution_code": notice.institution.code if hasattr(notice.institution, 'code') else 'N/A',
        }

        organization = get_user_institution(request.user)
        filename = f"notice_{notice.id}_{timezone.now().strftime('%Y%m%d_%H%M%S')}"

        # Generate QR code for notice
        qr_code_img = qr_generate(f"Notice: {notice.title} - ID: {notice.id}")

        if format_type == 'csv':
            return self.export_csv(row, filename, organization, audience_details)
        elif format_type == 'excel':
            return self.export_excel(row, filename, organization, audience_details)
        elif format_type == 'pdf':
            return self.export_pdf(row, filename, notice, organization, audience_details, qr_code_img)
        else:
            return HttpResponse("Invalid format specified", status=400)

    def export_csv(self, row, filename, organization, audience_details):
        buffer = StringIO()
        writer = csv.writer(buffer)

        # Notice details header
        writer.writerow(['NOTICE DETAILS'])
        writer.writerow([])
        
        # Notice information
        writer.writerow(['Title:', row['title']])
        writer.writerow(['Content:', row['content']])
        writer.writerow(['Priority:', row['priority']])
        writer.writerow(['Audience:', row['audience']])
        writer.writerow(['Status:', row['is_published']])
        writer.writerow(['Publish Date:', row['publish_date']])
        writer.writerow(['Expiry Date:', row['expiry_date']])
        writer.writerow(['Attachment:', row['attachment']])
        writer.writerow(['Created By:', row['created_by']])
        writer.writerow(['Created At:', row['created_at']])
        writer.writerow(['Updated At:', row['updated_at']])
        writer.writerow([])
        
        # Audience statistics
        writer.writerow(['AUDIENCE STATISTICS'])
        writer.writerow(['Total Audience:', row['total_audience']])
        writer.writerow(['Read Count:', row['read_count']])
        writer.writerow(['Unread Count:', row['unread_count']])
        writer.writerow(['Read Percentage:', row['read_percentage']])
        writer.writerow([])
        
        # Audience details
        writer.writerow(['AUDIENCE DETAILS'])
        writer.writerow(['User', 'Email', 'Status', 'Read At'])
        
        for audience in audience_details:
            writer.writerow([
                audience.user.get_full_name(),
                audience.user.email,
                'Read' if audience.read else 'Unread',
                audience.read_at.strftime('%Y-%m-%d %H:%M:%S') if audience.read_at else 'Not Read'
            ])
        
        writer.writerow([])
        writer.writerow(['Organization:', organization.name if organization else 'N/A'])
        writer.writerow(['Export Date:', timezone.now().strftime("%Y-%m-%d %H:%M")])

        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response

    def export_excel(self, row, filename, organization, audience_details):
        buffer = BytesIO()
        with xlsxwriter.Workbook(buffer) as workbook:
            # Notice Details sheet
            worksheet = workbook.add_worksheet('Notice Details')

            header_format = workbook.add_format({
                'bold': True, 
                'bg_color': '#3b5998', 
                'font_color': 'white', 
                'border': 1
            })
            label_format = workbook.add_format({'bold': True})
            
            # Notice Information
            worksheet.write(0, 0, 'NOTICE DETAILS', header_format)
            worksheet.merge_range(0, 0, 0, 3, 'NOTICE DETAILS', header_format)
            
            details = [
                ('Title:', row['title']),
                ('Content:', row['content']),
                ('Priority:', row['priority']),
                ('Audience:', row['audience']),
                ('Status:', row['is_published']),
                ('Publish Date:', row['publish_date']),
                ('Expiry Date:', row['expiry_date']),
                ('Attachment:', row['attachment']),
                ('Created By:', row['created_by']),
                ('Created At:', row['created_at']),
                ('Updated At:', row['updated_at']),
            ]
            
            for idx, (label, value) in enumerate(details, start=2):
                worksheet.write(idx, 0, label, label_format)
                worksheet.write(idx, 1, value)
            
            # Audience Statistics
            stats_row = len(details) + 4
            worksheet.write(stats_row, 0, 'AUDIENCE STATISTICS', header_format)
            worksheet.merge_range(stats_row, 0, stats_row, 3, 'AUDIENCE STATISTICS', header_format)
            
            stats = [
                ('Total Audience:', row['total_audience']),
                ('Read Count:', row['read_count']),
                ('Unread Count:', row['unread_count']),
                ('Read Percentage:', row['read_percentage']),
            ]
            
            for idx, (label, value) in enumerate(stats, start=stats_row + 1):
                worksheet.write(idx, 0, label, label_format)
                worksheet.write(idx, 1, value)
            
            # Audience Details sheet
            audience_sheet = workbook.add_worksheet('Audience Details')
            audience_sheet.write(0, 0, 'AUDIENCE DETAILS', header_format)
            audience_sheet.merge_range(0, 0, 0, 3, 'AUDIENCE DETAILS', header_format)
            
            # Headers
            headers = ['User', 'Email', 'Status', 'Read At']
            for col, header in enumerate(headers):
                audience_sheet.write(2, col, header, header_format)
            
            # Data
            for row_idx, audience in enumerate(audience_details, start=3):
                audience_sheet.write(row_idx, 0, audience.user.get_full_name())
                audience_sheet.write(row_idx, 1, audience.user.email)
                audience_sheet.write(row_idx, 2, 'Read' if audience.read else 'Unread')
                audience_sheet.write(row_idx, 3, 
                    audience.read_at.strftime('%Y-%m-%d %H:%M:%S') if audience.read_at else 'Not Read')
            
            # Adjust column widths
            worksheet.set_column('A:A', 20)
            worksheet.set_column('B:B', 40)
            audience_sheet.set_column('A:D', 25)
            
            # Summary
            summary_row = len(details) + len(stats) + 6
            worksheet.write(summary_row, 0, 'Organization:')
            worksheet.write(summary_row, 1, organization.name if organization else 'N/A')
            worksheet.write(summary_row + 1, 0, 'Export Date:')
            worksheet.write(summary_row + 1, 1, timezone.now().strftime("%Y-%m-%d %H:%M"))

        buffer.seek(0)
        response = HttpResponse(
            buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return response

    def export_pdf(self, row, filename, notice, organization, audience_details, qr_code_img):
        context = {
            "notice": row,
            "audience_details": audience_details,
            "organization": organization,
            "export_date": timezone.now(),
            "logo": getattr(organization.logo, 'url', None) if organization and organization.logo else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and organization.stamp else None,
            "title": f"Notice Detail - {notice.title}",
            "qr_code": qr_code_img,
        }
        pdf_bytes = render_to_pdf("communications/export/notice_detail_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)


class BroadcastExportView( StaffRequiredMixin, ListView):
    model = Broadcast
    context_object_name = 'broadcasts'
    
    def get_queryset(self):
        queryset = super().get_queryset()
        institution = get_user_institution(self.request.user)
        
        if institution:
            queryset = queryset.filter(institution=institution)
        
        return queryset.order_by('-created_at')
    
    def get(self, request, *args, **kwargs):
        format_type = request.GET.get('format', 'csv').lower()
        queryset = self.get_queryset()
        
        filename = f"broadcasts_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        rows = []
        for broadcast in queryset:
            rows.append({
                "name": broadcast.name,
                "audience": broadcast.get_audience_display(),
                "channel": broadcast.get_channel_display(),
                "message": broadcast.message,
                "status": broadcast.get_status_display(),
                "template": broadcast.template.name if broadcast.template else 'No Template',
                "scheduled_for": broadcast.scheduled_for.strftime('%Y-%m-%d %H:%M:%S') if broadcast.scheduled_for else 'Immediate',
                "total_recipients": broadcast.total_recipients,
                "successful": broadcast.successful,
                "failed": broadcast.failed,
                "success_rate": f"{(broadcast.successful/broadcast.total_recipients*100):.1f}%" if broadcast.total_recipients > 0 else "0%",
                "created_by": broadcast.created_by.get_full_name(),
                "created_at": broadcast.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            })

        organization = get_user_institution(request.user)
        
        if format_type == 'csv':
            return self.export_csv(rows, filename, organization)
        elif format_type == 'excel':
            return self.export_excel(rows, filename, organization)
        elif format_type == 'pdf':
            return self.export_pdf(rows, filename, organization, queryset.count())
        else:
            return HttpResponse("Invalid format specified", status=400)
    
    def export_csv(self, rows, filename, organization):
        buffer = StringIO()
        writer = csv.writer(buffer)
        
        writer.writerow([
            'Name', 'Audience', 'Channel', 'Message Preview', 'Status', 
            'Template', 'Scheduled For', 'Total Recipients', 'Successful', 
            'Failed', 'Success Rate', 'Created By', 'Created At'
        ])
        
        for row in rows:
            writer.writerow([
                row['name'],
                row['audience'],
                row['channel'],
                row['message'][:100] + '...' if len(row['message']) > 100 else row['message'],
                row['status'],
                row['template'],
                row['scheduled_for'],
                row['total_recipients'],
                row['successful'],
                row['failed'],
                row['success_rate'],
                row['created_by'],
                row['created_at']
            ])
        
        writer.writerow([])
        writer.writerow(['Total Broadcasts:', len(rows)])
        writer.writerow(['Organization:', organization.name if organization else 'N/A'])
        writer.writerow(['Export Date:', timezone.now().strftime("%Y-%m-%d %H:%M")])
        
        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response
    
    # --- PDF ---
    def export_pdf(self, rows, filename, organization,count):
        # Generate QR code for reference
        qr_code_img = qr_generate(f"Broadcast Export - {datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        context = {
            "broadcasts": rows,
            "organization": organization,
            "export_date": timezone.now(),
            "logo": getattr(organization.logo, 'url', None) if organization and hasattr(organization, 'logo') else None,
            "stamp": getattr(organization.stamp, 'url', None) if organization and hasattr(organization, 'stamp') else None,
            "title": "Broadcasts Export",
            "qr_code": qr_code_img,
        }
        pdf_bytes = render_to_pdf("communications/export/broadcasts_list_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=500)



# 
# Add to existing views.py
class NoticeAudienceListView( StaffRequiredMixin, ListView):
    model = NoticeAudience
    template_name = 'communications/notice_audience/audience_list.html'
    context_object_name = 'audience_members'
    paginate_by = 25

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        queryset = NoticeAudience.objects.filter(notice__institution=institution)
        
        # Filter by notice if provided
        notice_id = self.request.GET.get('notice')
        if notice_id:
            queryset = queryset.filter(notice_id=notice_id)
        
        # Filter by read status
        read_status = self.request.GET.get('read_status')
        if read_status == 'read':
            queryset = queryset.filter(read=True)
        elif read_status == 'unread':
            queryset = queryset.filter(read=False)
        
        # Filter by delivery status
        delivery_status = self.request.GET.get('delivery_status')
        if delivery_status == 'delivered':
            queryset = queryset.filter(delivered=True)
        elif delivery_status == 'undelivered':
            queryset = queryset.filter(delivered=False)
        
        # Search by user name or email
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__email__icontains=search)
            )
        
        return queryset.select_related('notice', 'user').order_by('-notice__publish_date', 'user__first_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institution = get_user_institution(self.request.user)
        
        # Get statistics
        queryset = self.get_queryset()
        total_count = queryset.count()
        read_count = queryset.filter(read=True).count()
        delivered_count = queryset.filter(delivered=True).count()
        
        context.update({
            'total_count': total_count,
            'read_count': read_count,
            'unread_count': total_count - read_count,
            'delivered_count': delivered_count,
            'undelivered_count': total_count - delivered_count,
            'read_percentage': (read_count / total_count * 100) if total_count > 0 else 0,
            'delivery_percentage': (delivered_count / total_count * 100) if total_count > 0 else 0,
            'notices': Notice.objects.filter(institution=institution, is_published=True),
        })
        return context


class NoticeAudienceDetailView( StaffRequiredMixin, DetailView):
    model = NoticeAudience
    template_name = 'communications/notice_audience/audience_detail.html'
    context_object_name = 'audience_member'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return NoticeAudience.objects.filter(notice__institution=institution)


class NoticeAudienceUpdateView( StaffRequiredMixin, UpdateView):
    model = NoticeAudience
    template_name = 'communications/notice_audience/audience_form.html'
    context_object_name = 'audience_member'
    fields = ['read', 'delivered', 'notification_sent']

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return NoticeAudience.objects.filter(notice__institution=institution)

    def form_valid(self, form):
        # Update timestamps based on status changes
        if form.cleaned_data['read'] and not self.object.read:
            form.instance.read_at = timezone.now()
        
        if form.cleaned_data['delivered'] and not self.object.delivered:
            form.instance.delivered_at = timezone.now()
        
        messages.success(self.request, "Audience member updated successfully!")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('communications:audience_list')


class NoticeAudienceDeleteView( StaffRequiredMixin, DeleteView):
    model = NoticeAudience
    template_name = 'communications/notice_audience/audience_confirm_delete.html'
    context_object_name = 'audience_member'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return NoticeAudience.objects.filter(notice__institution=institution)

    def get_success_url(self):
        messages.success(self.request, "Audience member removed successfully!")
        return reverse('communications:audience_list')


class NoticeAudienceBulkActionView( StaffRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        audience_ids = request.POST.getlist('audience_ids')
        
        if not audience_ids:
            messages.error(request, "No audience members selected.")
            return redirect('communications:audience_list')
        
        institution = get_user_institution(request.user)
        audience_members = NoticeAudience.objects.filter(
            id__in=audience_ids,
            notice__institution=institution
        )
        
        if action == 'mark_read':
            count = 0
            for audience in audience_members:
                if not audience.read:
                    audience.mark_as_read()
                    count += 1
            messages.success(request, f"Marked {count} audience members as read.")
        
        elif action == 'mark_unread':
            updated = audience_members.filter(read=True).update(
                read=False, 
                read_at=None
            )
            messages.success(request, f"Marked {updated} audience members as unread.")
        
        elif action == 'mark_delivered':
            count = 0
            for audience in audience_members:
                if not audience.delivered:
                    audience.mark_as_delivered()
                    count += 1
            messages.success(request, f"Marked {count} audience members as delivered.")
        
        elif action == 'delete':
            count = audience_members.count()
            audience_members.delete()
            messages.success(request, f"Deleted {count} audience members.")
        
        return redirect('communications:audience_list')


class NoticeAudienceExportView( StaffRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        format_type = request.GET.get('format', 'csv').lower()
        institution = get_user_institution(request.user)
        
        # Apply filters
        queryset = NoticeAudience.objects.filter(notice__institution=institution)
        
        notice_id = request.GET.get('notice')
        if notice_id:
            queryset = queryset.filter(notice_id=notice_id)
        
        read_status = request.GET.get('read_status')
        if read_status == 'read':
            queryset = queryset.filter(read=True)
        elif read_status == 'unread':
            queryset = queryset.filter(read=False)
        
        delivery_status = request.GET.get('delivery_status')
        if delivery_status == 'delivered':
            queryset = queryset.filter(delivered=True)
        elif delivery_status == 'undelivered':
            queryset = queryset.filter(delivered=False)
        
        search = request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(user__first_name__icontains=search) |
                Q(user__last_name__icontains=search) |
                Q(user__email__icontains=search)
            )
        
        queryset = queryset.select_related('notice', 'user').order_by('-notice__publish_date', 'user__first_name')
        
        filename = f"notice_audience_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
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
            'Notice Title', 'User Name', 'User Email', 'Read Status', 
            'Read At', 'Delivery Status', 'Delivered At', 
            'Notification Sent', 'Notice Publish Date'
        ])
        
        # Write data rows
        for audience in queryset:
            writer.writerow([
                audience.notice.title,
                audience.user.get_full_name(),
                audience.user.email,
                'Read' if audience.read else 'Unread',
                audience.read_at.strftime('%Y-%m-%d %H:%M:%S') if audience.read_at else 'Not Read',
                'Delivered' if audience.delivered else 'Not Delivered',
                audience.delivered_at.strftime('%Y-%m-%d %H:%M:%S') if audience.delivered_at else 'Not Delivered',
                'Yes' if audience.notification_sent else 'No',
                audience.notice.publish_date.strftime('%Y-%m-%d %H:%M:%S') if audience.notice.publish_date else 'Not Published'
            ])
        
        # Add summary
        total_count = queryset.count()
        read_count = queryset.filter(read=True).count()
        delivered_count = queryset.filter(delivered=True).count()
        
        writer.writerow([])
        writer.writerow(['Summary Statistics'])
        writer.writerow(['Total Records:', total_count])
        writer.writerow(['Read Count:', read_count])
        writer.writerow(['Unread Count:', total_count - read_count])
        writer.writerow(['Delivered Count:', delivered_count])
        writer.writerow(['Read Percentage:', f'{(read_count/total_count*100):.1f}%' if total_count > 0 else '0%'])
        writer.writerow(['Organization:', institution.name if institution else 'N/A'])
        writer.writerow(['Export Date:', timezone.now().strftime("%Y-%m-%d %H:%M")])
        
        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response
    
    def export_excel(self, queryset, filename, institution):
        buffer = BytesIO()
        
        with xlsxwriter.Workbook(buffer) as workbook:
            worksheet = workbook.add_worksheet('Notice Audience')
            
            # Formats
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#3b5998',
                'font_color': 'white',
                'border': 1,
                'align': 'center'
            })
            
            date_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm:ss'})
            center_format = workbook.add_format({'align': 'center'})
            
            # Headers
            headers = [
                'Notice Title', 'User Name', 'User Email', 'Read Status', 
                'Read At', 'Delivery Status', 'Delivered At', 
                'Notification Sent', 'Notice Publish Date'
            ]
            
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)
            
            # Data
            for row_idx, audience in enumerate(queryset, start=1):
                worksheet.write(row_idx, 0, audience.notice.title)
                worksheet.write(row_idx, 1, audience.user.get_full_name())
                worksheet.write(row_idx, 2, audience.user.email)
                worksheet.write(row_idx, 3, 'Read' if audience.read else 'Unread', center_format)
                worksheet.write(row_idx, 4, audience.read_at.strftime('%Y-%m-%d %H:%M:%S') if audience.read_at else 'Not Read', date_format)
                worksheet.write(row_idx, 5, 'Delivered' if audience.delivered else 'Not Delivered', center_format)
                worksheet.write(row_idx, 6, audience.delivered_at.strftime('%Y-%m-%d %H:%M:%S') if audience.delivered_at else 'Not Delivered', date_format)
                worksheet.write(row_idx, 7, 'Yes' if audience.notification_sent else 'No', center_format)
                worksheet.write(row_idx, 8, audience.notice.publish_date.strftime('%Y-%m-%d %H:%M:%S') if audience.notice.publish_date else 'Not Published', date_format)
            
            # Adjust columns
            worksheet.set_column('A:A', 40)  # Notice Title
            worksheet.set_column('B:B', 25)  # User Name
            worksheet.set_column('C:C', 30)  # User Email
            worksheet.set_column('D:D', 15)  # Read Status
            worksheet.set_column('E:E', 20)  # Read At
            worksheet.set_column('F:F', 15)  # Delivery Status
            worksheet.set_column('G:G', 20)  # Delivered At
            worksheet.set_column('H:H', 15)  # Notification Sent
            worksheet.set_column('I:I', 20)  # Publish Date
            
            # Summary
            total_count = queryset.count()
            read_count = queryset.filter(read=True).count()
            delivered_count = queryset.filter(delivered=True).count()
            
            summary_row = len(queryset) + 3
            worksheet.write(summary_row, 0, 'Summary Statistics', header_format)
            worksheet.merge_range(summary_row, 0, summary_row, 1, 'Summary Statistics', header_format)
            
            worksheet.write(summary_row + 1, 0, 'Total Records:')
            worksheet.write(summary_row + 1, 1, total_count)
            
            worksheet.write(summary_row + 2, 0, 'Read Count:')
            worksheet.write(summary_row + 2, 1, read_count)
            
            worksheet.write(summary_row + 3, 0, 'Organization:')
            worksheet.write(summary_row + 3, 1, institution.name if institution else 'N/A')
            
            worksheet.write(summary_row + 4, 0, 'Export Date:')
            worksheet.write(summary_row + 4, 1, timezone.now().strftime("%Y-%m-%d %H:%M"))
        
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
        for audience in queryset:
            rows.append({
                'notice_title': audience.notice.title,
                'user_name': audience.user.get_full_name(),
                'user_email': audience.user.email,
                'read_status': 'Read' if audience.read else 'Unread',
                'read_at': audience.read_at.strftime('%Y-%m-%d %H:%M:%S') if audience.read_at else 'Not Read',
                'delivery_status': 'Delivered' if audience.delivered else 'Not Delivered',
                'delivered_at': audience.delivered_at.strftime('%Y-%m-%d %H:%M:%S') if audience.delivered_at else 'Not Delivered',
                'notification_sent': 'Yes' if audience.notification_sent else 'No',
                'publish_date': audience.notice.publish_date.strftime('%Y-%m-%d %H:%M:%S') if audience.notice.publish_date else 'Not Published'
            })
        
        context = {
            "audience_members": rows,
            "total_count": queryset.count(),
            "read_count": queryset.filter(read=True).count(),
            "delivered_count": queryset.filter(delivered=True).count(),
            "organization": institution,
            "export_date": timezone.now(),
            "title": "Notice Audience Export",
        }
        
        pdf_bytes = render_to_pdf("communications/export/audience_list_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=400)