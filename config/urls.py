from django.urls import path, include
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Authentication
    path('accounts/', include('allauth.urls')),
    
    # Dashboard
    path('', include('apps.core.urls')),
    path('users/', include('apps.users.urls')),
    # path('users/', include('apps.users.urls')),
    path('reports/', include('apps.reports.urls')),
    
    # Apps
    path('students/', include('apps.students.urls')),
    path('teachers/', include('apps.teachers.urls')),
    path('academics/', include('apps.academics.urls')),
    path('attendance/', include('apps.attendance.urls')),
    path('hostel/', include('apps.hostel.urls')),
    path('examination/', include('apps.examination.urls')),
    path('finance/', include('apps.finance.urls')),
    path('library/', include('apps.library.urls')),
    path('inventory/', include('apps.inventory.urls')),
    path('transportation/', include('apps.transportation.urls')),
    path('hr/', include('apps.hr.urls')),
    path('communications/', include('apps.communications.urls')),
    path('organization/', include('apps.organization.urls')),
    
    # API
    # path('api/', include('apps.api.urls')),
    
    # Payments
    path('payments/', include('apps.payments.urls')),

    path('student-portal/', include('apps.student_portal.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)