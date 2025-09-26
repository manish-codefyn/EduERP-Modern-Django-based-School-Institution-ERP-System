from apps.organization.models import Institution
from apps.communications.models import PushNotification
from apps.core.utils import get_user_institution
from django.db.models import Q, Count
from django.utils import timezone

def organization_context(request):
    try:
        org = Institution.objects.filter(is_active=True).first()
    except Institution.DoesNotExist:
        org = None
    return {
        "organization": org
    }

def role_flags(request):
    user = request.user
    return {
        "is_superadmin": getattr(user, "is_superadmin", False),
        "is_institution_admin": getattr(user, "is_institution_admin", False),
        "is_principal": getattr(user, "is_principal", False),
        "is_accountant": getattr(user, "is_accountant", False),
        "is_teacher": getattr(user, "is_teacher", False),
        "is_student": getattr(user, "is_student", False),
        "is_parent": getattr(user, "is_parent", False),
        "is_librarian": getattr(user, "is_librarian", False),
        "is_transport_manager": getattr(user, "is_transport_manager", False),
        "is_hr": getattr(user, "is_hr", False),
    }

def header_notifications(request):
    """
    Add push notifications to header context for all templates
    """
    context = {
        "header_notifications_count": 0,
        "header_notifications_list": [],
        "notification_stats": {},
        "has_notification_permission": False,
    }
    
    if not request.user.is_authenticated:
        return context

    try:
        institution = get_user_institution(request.user)
        if not institution:
            return context

        # Check user permissions for notifications
        user_roles = role_flags(request)
        has_notification_permission = any([
            user_roles.get('is_superadmin', False),
            user_roles.get('is_institution_admin', False),
            user_roles.get('is_principal', False),
            user_roles.get('is_hr', False),
        ])
        
        context["has_notification_permission"] = has_notification_permission

        if not has_notification_permission:
            return context

        # Notification counts by status
        notifications = PushNotification.objects.filter(institution=institution)
        
        # Status counts for dashboard
        status_counts = notifications.values('status').annotate(count=Count('id'))
        status_dict = {item['status']: item['count'] for item in status_counts}
        
        # Pending notifications (for badge count)
        pending_notifications = notifications.filter(
            Q(status='draft') | Q(status='scheduled')
        )
        
        # Latest notifications for dropdown
        latest_notifications = notifications.select_related('created_by').order_by('-created_at')[:5]
        
        # Today's notifications
        today = timezone.now().date()
        todays_notifications = notifications.filter(created_at__date=today).count()
        
        # Statistics for notification dashboard
        total_sent = notifications.filter(status='sent').aggregate(
            total_recipients=Count('total_recipients'),
            successful=Count('successful')
        )
        
        success_rate = 0
        if total_sent['total_recipients'] and total_sent['total_recipients'] > 0:
            success_rate = (total_sent['successful'] / total_sent['total_recipients']) * 100

        context.update({
            "header_notifications_count": pending_notifications.count(),
            "header_notifications_list": latest_notifications,
            "notification_stats": {
                'total': notifications.count(),
                'draft': status_dict.get('draft', 0),
                'scheduled': status_dict.get('scheduled', 0),
                'sent': status_dict.get('sent', 0),
                'failed': status_dict.get('failed', 0),
                'today': todays_notifications,
                'success_rate': round(success_rate, 1),
                'pending': pending_notifications.count(),
            },
            "can_create_notification": user_roles.get('is_superadmin', False) or 
                                     user_roles.get('is_institution_admin', False),
        })

    except Exception as e:
        # Log error but don't break the template
        print(f"Error in header_notifications context processor: {e}")
        # Return basic context without notifications

    return context