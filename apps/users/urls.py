# accounts/urls.py
from django.urls import path
from django.contrib.auth.decorators import login_required
from .views import *
from .profile import*



urlpatterns = [
    # Two main dashboard URLs
    path('dashboard/student-parent/', login_required(StudentParentDashboardView.as_view()), 
         name='student_parent_dashboard'),
    path('dashboard/admin-main/', login_required(AdminMainDashboardView.as_view()), 
         name='admin_main_dashboard'),
    
    # Fallback
#     path('profile/', login_required(ProfileView.as_view()), name='profile'),

    # User profile URLs
    path('profile/', UserProfileView.as_view(), name='users_profile'),
    path('profile/edit/', UserProfileUpdateView.as_view(), name='users_profile_edit'),
    
    # All Auth compatible password change URLs
    path('password/change/', AllAuthPasswordChangeView.as_view(), 
         name='account_change_password'),
    path('password/set/', AllAuthPasswordSetView.as_view(), 
         name='account_set_password'),
    
    # Additional security URLs
#     path('password/reset/', PasswordResetView.as_view(
#         form_class=AllAuthPasswordResetForm
#     ), name='account_reset_password'),
    
    # Backward compatibility URLs
    path('profile/security/', AllAuthPasswordChangeView.as_view(), 
         name='users_security'),


#     Avatar management
    path('profile/avatar/upload/', AvatarUploadView.as_view(), name='avatar_upload'),
    path('profile/avatar/remove/', AvatarRemoveView.as_view(), name='avatar_remove'),

]