# student_portal/urls.py
from django.urls import path
from . import views

app_name = 'student_portal'

urlpatterns = [
    path('dashboard/', views.StudentDashboardView.as_view(), name='dashboard'),
    path('timetable/', views.StudentTimetableView.as_view(), name='timetable'),
    path('grades/', views.StudentGradesView.as_view(), name='grades'),
    path('attendance/', views.StudentAttendanceView.as_view(), name='attendance'),
    path('resources/', views.StudentResourcesView.as_view(), name='resources'),
    path('profile/', views.StudentProfileView.as_view(), name='profile'),
]