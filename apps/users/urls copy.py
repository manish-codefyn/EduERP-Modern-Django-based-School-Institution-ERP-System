# accounts/urls.py
from django.urls import path
from django.contrib.auth.decorators import login_required
from .views import *

urlpatterns = [
    # Dashboard URLs
    path('admin/dashboard/', login_required(AdminDashboardView.as_view()), name='admin_dashboard'),
    path('institution/dashboard/', login_required(InstitutionDashboardView.as_view()), name='institution_dashboard'),
    path('principal/dashboard/', login_required(PrincipalDashboardView.as_view()), name='principal_dashboard'),
    path('teacher/dashboard/', login_required(TeacherDashboardView.as_view()), name='teacher_dashboard'),
    path('student/dashboard/', login_required(StudentDashboardView.as_view()), name='student_dashboard'),
    path('parent/dashboard/', login_required(ParentDashboardView.as_view()), name='parent_dashboard'),
    path('accountant/dashboard/', login_required(AccountantDashboardView.as_view()), name='accountant_dashboard'),
    path('librarian/dashboard/', login_required(LibrarianDashboardView.as_view()), name='librarian_dashboard'),
    path('transport/dashboard/', login_required(TransportManagerDashboardView.as_view()), name='transport_dashboard'),
    path('hr/dashboard/', login_required(HRDashboardView.as_view()), name='hr_dashboard'),
    path('support/dashboard/', login_required(SupportStaffDashboardView.as_view()), name='support_dashboard'),
    path('library/manager/dashboard/', login_required(LibraryManagerDashboardView.as_view()), name='library_dashboard'),
    
    # Utility URLs
    path('profile/', login_required(ProfileView.as_view()), name='profile'),
    path('access-denied/', AccessDeniedView.as_view(), name='access_denied'),
    path('redirect/', role_based_redirect, name='role_redirect'),
]