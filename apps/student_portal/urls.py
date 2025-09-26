from django.urls import path
from . import views

app_name = 'student_portal'

urlpatterns = [
    # Student Portal URLs
    path('portal/', views.StudentPortalDashboard.as_view(), name='dashboard'),
    path('portal/fun-game/', views.StudentFunGame.as_view(), name='fun_game'),
    path('portal/academics/', views.AcademicOverview.as_view(), name='academic_overview'),
    # path('portal/attendance/', views.AttendanceView.as_view(), name='attendance'),
    path('portal/fees/', views.FeeView.as_view(), name='fees'),
    path('portal/library/', views.LibraryView.as_view(), name='library'),
    path('portal/hostel/', views.HostelView.as_view(), name='hostel'),
    path('portal/notifications/', views.NotificationListView.as_view(), name='notifications'),
    path('portal/timetable/', views.StudentTimetableView.as_view(), name='timetable'),

    path('grades/', views.StudentGradesView.as_view(), name='grades'),
    path('attendance/', views.StudentAttendanceView.as_view(), name='attendance'),
    path('resources/', views.StudentResourcesView.as_view(), name='resources'),
    path('profile/', views.StudentProfileView.as_view(), name='profile'),
    # AJAX endpoints
    path('portal/notifications/<uuid:pk>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('portal/notifications/read-all/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('portal/settings/update/', views.update_portal_settings, name='update_portal_settings'),
    
    # Keep your existing student URLs
    # path('<uuid:pk>/', views.StudentDetailView.as_view(), name='student_detail'),
    # ... your existing URLs
]