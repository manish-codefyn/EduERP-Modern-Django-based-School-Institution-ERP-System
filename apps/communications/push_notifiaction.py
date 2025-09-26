

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
from apps.core.mixins import StaffRequiredMixin ,DirectorRequiredMixin

from .models import PushNotification
from .forms import NoticeForm, BroadcastForm, NotificationTemplateForm,PushNotificationForm





# Push Notification Views

class PushNotificationListView( StaffRequiredMixin, ListView):
    model = PushNotification
    template_name = 'communications/push_notification/push_notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 25

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        queryset = PushNotification.objects.filter(institution=institution)
        
        # Filters
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        priority = self.request.GET.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        audience = self.request.GET.get('audience')
        if audience:
            queryset = queryset.filter(audience=audience)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(message__icontains=search)
            )
        
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        return queryset.select_related('template').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        queryset = self.get_queryset()
        total_count = queryset.count()
        status_counts = queryset.values('status').annotate(count=Count('id'))
        context.update({
            'total_count': total_count,
            'status_counts': {item['status']: item['count'] for item in status_counts},
        })
        return context


class PushNotificationDetailView( StaffRequiredMixin, DetailView):
    model = PushNotification
    template_name = 'communications/push_notification/push_notification_detail.html'
    context_object_name = 'notification'

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return PushNotification.objects.filter(institution=institution)



class PushNotificationCreateView( DirectorRequiredMixin, CreateView):
    model = PushNotification
    form_class = PushNotificationForm
    template_name = 'communications/push_notification/push_notification_form.html'
    success_url = reverse_lazy('communications:push_notification_list')  # Redirect after success

    def form_valid(self, form):
        # Set the institution and creator automatically
        form.instance.institution = get_user_institution(self.request.user)
        form.instance.created_by = self.request.user
        return super().form_valid(form)


class PushNotificationDeleteView( DirectorRequiredMixin, DeleteView):
    model = PushNotification
    template_name = 'communications/push_notification/push_notification_confirm_delete.html'
    success_url = reverse_lazy('communications:push_notification_list')

    def get_queryset(self):
        institution = get_user_institution(self.request.user)
        return PushNotification.objects.filter(institution=institution)

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Push notification deleted successfully!")
        return super().delete(request, *args, **kwargs)


class PushNotificationExportView( StaffRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        format_type = request.GET.get('format', 'csv').lower()
        institution = get_user_institution(request.user)
        queryset = PushNotification.objects.filter(institution=institution)

        # Apply filters (status, priority, audience, date, search)
        status = request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        priority = request.GET.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        audience = request.GET.get('audience')
        if audience:
            queryset = queryset.filter(audience=audience)
        search = request.GET.get('search')
        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(message__icontains=search))
        date_from = request.GET.get('date_from')
        date_to = request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        filename = f"push_notifications_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
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
        writer.writerow([
            'Title', 'Message', 'Priority', 'Audience', 'Template',
            'Total Recipients', 'Successful', 'Failed', 'Scheduled For', 'Status', 'Created At'
        ])
        for notif in queryset:
            writer.writerow([
                notif.title,
                notif.message[:100] + '...' if len(notif.message) > 100 else notif.message,
                notif.get_priority_display(),
                notif.get_audience_display(),
                notif.template.name if notif.template else 'No Template',
                notif.total_recipients,
                notif.successful,
                notif.failed,
                notif.scheduled_for.strftime('%Y-%m-%d %H:%M:%S') if notif.scheduled_for else 'Immediate',
                notif.get_status_display(),
                notif.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            ])
        response = HttpResponse(buffer.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response

    def export_excel(self, queryset, filename, institution):
        buffer = BytesIO()
        with xlsxwriter.Workbook(buffer) as workbook:
            ws = workbook.add_worksheet("Push Notifications")
            header_format = workbook.add_format({'bold': True, 'bg_color': '#3b5998','font_color':'white'})
            headers = ['Title','Message','Priority','Audience','Template','Total Recipients','Successful','Failed','Scheduled For','Status','Created At']
            for col, h in enumerate(headers):
                ws.write(0, col, h, header_format)
            for row_idx, notif in enumerate(queryset, start=1):
                ws.write(row_idx, 0, notif.title)
                ws.write(row_idx, 1, notif.message)
                ws.write(row_idx, 2, notif.get_priority_display())
                ws.write(row_idx, 3, notif.get_audience_display())
                ws.write(row_idx, 4, notif.template.name if notif.template else 'No Template')
                ws.write(row_idx, 5, notif.total_recipients)
                ws.write(row_idx, 6, notif.successful)
                ws.write(row_idx, 7, notif.failed)
                ws.write(row_idx, 8, notif.scheduled_for.strftime('%Y-%m-%d %H:%M:%S') if notif.scheduled_for else 'Immediate')
                ws.write(row_idx, 9, notif.get_status_display())
                ws.write(row_idx, 10, notif.created_at.strftime('%Y-%m-%d %H:%M:%S'))
        buffer.seek(0)
        response = HttpResponse(buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = f'attachment; filename="{filename}.xlsx"'
        return response

    def export_pdf(self, queryset, filename, institution):
        rows = []
        for notif in queryset:
            rows.append({
                'title': notif.title,
                'message': notif.message,
                'priority': notif.get_priority_display(),
                'audience': notif.get_audience_display(),
                'template': notif.template.name if notif.template else 'No Template',
                'total_recipients': notif.total_recipients,
                'successful': notif.successful,
                'failed': notif.failed,
                'scheduled_for': notif.scheduled_for.strftime('%Y-%m-%d %H:%M:%S') if notif.scheduled_for else 'Immediate',
                'status': notif.get_status_display(),
                'created_at': notif.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            })
        context = {
            "notifications": rows,
            "total_count": queryset.count(),
            "organization": institution,
            "export_date": timezone.now(),
            "title": "Push Notifications Export",
        }
        pdf_bytes = render_to_pdf("communications/export/push_notifications_pdf.html", context)
        if pdf_bytes:
            return export_pdf_response(pdf_bytes, f"{filename}.pdf")
        return HttpResponse("Error generating PDF", status=400)
