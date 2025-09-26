from django.urls import path
from . import views


urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('students/', views.StudentReportView.as_view(), name='student_report'),
    path('attendance/', views.AttendanceReportView.as_view(), name='attendance_report'),
    path('financial/', views.FinancialReportView.as_view(), name='financial_report'),
    path('academic/', views.AcademicReportView.as_view(), name='academic_report'),
    # path('custom/', views.CustomReportView.as_view(), name='custom_report'),
]