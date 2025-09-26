from django.shortcuts import render, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.db.models import Q, Count
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .models import Notice, SMSLog, EmailLog, NotificationTemplate, Broadcast

class NoticeListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Notice
    template_name = 'communications/notice_list.html'
    permission_required = 'communications.view_notice'
    context_object_name = 'notices'
    
    def get_queryset(self):
        queryset = Notice.objects.filter(school=self.request.school)
        
        # Filter by audience if specified
        audience = self.request.GET.get('audience')
        if audience:
            queryset = queryset.filter(audience=audience)
        
        # Filter by priority if specified
        priority = self.request.GET.get('priority')
        if priority:
            queryset = queryset.filter(priority=priority)
        
        # Filter by published status
        published = self.request.GET.get('published')
        if published == 'yes':
            queryset = queryset.filter(is_published=True)
        elif published == 'no':
            queryset = queryset.filter(is_published=False)
        
        return queryset.select_related('created_by').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['audience_choices'] = Notice.AUDIENCE_CHOICES
        context['priority_choices'] = Notice.PRIORITY_CHOICES
        return context

class NoticeCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Notice
    fields = ['title', 'content', 'priority', 'audience', 'is_published', 'expiry_date', 'attachment']
    template_name = 'communications/notice_form.html'
    permission_required = 'communications.add_notice'
    success_url = reverse_lazy('notice_list')
    
    def form_valid(self, form):
        form.instance.school = self.request.school
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(self.request, 'Notice created successfully.')
        return response

class NoticeDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Notice
    template_name = 'communications/notice_detail.html'
    permission_required = 'communications.view_notice'
    
    def get_queryset(self):
        return Notice.objects.filter(school=self.request.school)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Mark as read for the current user
        notice_audience, created = self.object.audience_details.get_or_create(
            user=self.request.user
        )
        if not notice_audience.read:
            notice_audience.read = True
            notice_audience.read_at = timezone.now()
            notice_audience.save()
        
        # Get audience statistics
        audience_stats = self.object.audience_details.aggregate(
            total=Count('id'),
            read=Count('id', filter=Q(read=True)),
            unread=Count('id', filter=Q(read=False))
        )
        
        context['audience_stats'] = audience_stats
        return context

class SMSLogListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = SMSLog
    template_name = 'communications/sms_log.html'
    permission_required = 'communications.view_smslog'
    context_object_name = 'sms_logs'
    
    def get_queryset(self):
        queryset = SMSLog.objects.filter(school=self.request.school)
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = SMSLog.STATUS_CHOICES
        return context

class EmailLogListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = EmailLog
    template_name = 'communications/email_log.html'
    permission_required = 'communications.view_emaillog'
    context_object_name = 'email_logs'
    
    def get_queryset(self):
        queryset = EmailLog.objects.filter(school=self.request.school)
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = EmailLog.STATUS_CHOICES
        return context

class NotificationTemplateListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = NotificationTemplate
    template_name = 'communications/template_list.html'
    permission_required = 'communications.view_notificationtemplate'
    context_object_name = 'templates'
    
    def get_queryset(self):
        queryset = NotificationTemplate.objects.filter(school=self.request.school)
        template_type = self.request.GET.get('type')
        if template_type:
            queryset = queryset.filter(template_type=template_type)
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['type_choices'] = NotificationTemplate.TYPE_CHOICES
        return context

class BroadcastListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Broadcast
    template_name = 'communications/broadcast_list.html'
    permission_required = 'communications.view_broadcast'
    context_object_name = 'broadcasts'
    
    def get_queryset(self):
        return Broadcast.objects.filter(school=self.request.school).order_by('-created_at')