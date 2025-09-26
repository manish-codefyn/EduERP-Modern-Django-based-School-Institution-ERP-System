from django.urls import path
from . import views
from . import email_sms_logs
from . import push_notifiaction

app_name = 'communications'

urlpatterns = [

    path('push-notifications/',  push_notifiaction.PushNotificationListView.as_view(), name='push_notification_list'),
    path('push-notifications/<uuid:pk>/',  push_notifiaction.PushNotificationDetailView.as_view(), name='push_notification_detail'),
    path('push-notifications/<uuid:pk>/delete/',  push_notifiaction.PushNotificationDeleteView.as_view(), name='push_notification_delete'),
    path('push-notifications/export/',  push_notifiaction.PushNotificationExportView.as_view(), name='push_notification_export'),
    path('push-notifications/create/', push_notifiaction.PushNotificationCreateView.as_view(), name='push_notification_create'),

    # SMS Log URLs
    path('sms-logs/', email_sms_logs.SMSLogListView.as_view(), name='sms_log_list'),
    path('sms-logs/<uuid:pk>/', email_sms_logs.SMSLogDetailView.as_view(), name='sms_log_detail'),
    path('sms-logs/<uuid:pk>/delete/', email_sms_logs.SMSLogDeleteView.as_view(), name='sms_log_delete'),
    path('sms-logs/export/', email_sms_logs.SMSLogExportView.as_view(), name='sms_log_export'),

    # Email Log URLs
    path('email-logs/', email_sms_logs.EmailLogListView.as_view(), name='email_log_list'),
    path('email-logs/<uuid:pk>/', email_sms_logs.EmailLogDetailView.as_view(), name='email_log_detail'),
    path('email-logs/<uuid:pk>/delete/', email_sms_logs.EmailLogDeleteView.as_view(), name='email_log_delete'),
    path('email-logs/export/', email_sms_logs.EmailLogExportView.as_view(), name='email_log_export'),

    # Notice Audience URLs
    path('notice-audience/', views.NoticeAudienceListView.as_view(), name='audience_list'),
    path('notice-audience/<uuid:pk>/', views.NoticeAudienceDetailView.as_view(), name='audience_detail'),
    path('notice-audience/<uuid:pk>/update/', views.NoticeAudienceUpdateView.as_view(), name='audience_update'),
    path('notice-audience/<uuid:pk>/delete/', views.NoticeAudienceDeleteView.as_view(), name='audience_delete'),
    path('notice-audience/bulk-action/', views.NoticeAudienceBulkActionView.as_view(), name='audience_bulk_action'),
    path('notice-audience/export/', views.NoticeAudienceExportView.as_view(), name='audience_export'),
   
    # Notice URLs
    path('notices/', views.NoticeListView.as_view(), name='notice_list'),
    path('notices/create/', views.NoticeCreateView.as_view(), name='notice_create'),
    path('notices/<uuid:pk>/', views.NoticeDetailView.as_view(), name='notice_detail'),
    path('notices/<uuid:pk>/update/', views.NoticeUpdateView.as_view(), name='notice_update'),
    path('notices/<uuid:pk>/delete/', views.NoticeDeleteView.as_view(), name='notice_delete'),
    path('notices/export/', views.NoticeExportView.as_view(), name='notice_export'),
    path('notices/<uuid:pk>/export/', views.NoticeDetailExportView.as_view(), name='notice_detail_export'),
    # Broadcast URLs
    path('broadcasts/', views.BroadcastListView.as_view(), name='broadcast_list'),
    path('broadcasts/create/', views.BroadcastCreateView.as_view(), name='broadcast_create'),
    path('broadcasts/<uuid:pk>/', views.BroadcastDetailView.as_view(), name='broadcast_detail'),
    path('broadcasts/<uuid:pk>/update', views.BroadcastUpdateView.as_view(), name='broadcast_update'),
    path('broadcast/<uuid:pk>/delete/',views.BroadcastDeleteView.as_view(),name='broadcast_delete'),
    path('broadcasts/export/', views.BroadcastExportView.as_view(), name='broadcast_export'),
    # Template URLs
    path('templates/', views.NotificationTemplateListView.as_view(), name='template_list'),
    path('templates/create/', views.NotificationTemplateCreateView.as_view(), name='template_create'),
    path('templates/<uuid:pk>/', views.NotificationTemplateDetailView.as_view(), name='template_detail'),
    path('templates/<uuid:pk>/update', views.NotificationTemplateUpdateView.as_view(), name='template_update'),
    path('templates/<uuid:pk>/delete/',views.NotificationTemplateDeleteView.as_view(),name='template_delete'),
   
    
    path('dashboard/', views.CommunicationsDashboardView.as_view(), name='dashboard'),

]