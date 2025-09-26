# account/views.py
from django.views.generic import DetailView, UpdateView, TemplateView, FormView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect
from django.http import JsonResponse
from allauth.account.views import PasswordChangeView as AllAuthPasswordChangeView
from allauth.account.views import PasswordSetView as AllAuthPasswordSetView
from .models import User, UserProfile
from .forms import AllAuthCompatibleSecurityForm, UserProfileForm, AllAuthCompatibleSetPasswordForm,UserAvatarForm
from django.utils.translation import gettext_lazy as _


class AllAuthPasswordChangeView(AllAuthPasswordChangeView):
    """
    Custom password change view that uses our enhanced form
    while maintaining All Auth functionality
    """
    form_class = AllAuthCompatibleSecurityForm
    template_name = 'account/user_security.html'
    
    def get_success_url(self):
        messages.success(self.request, _('Your password has been changed successfully!'))
        return reverse_lazy('users_profile')
    
    def form_invalid(self, form):
        messages.error(self.request, _('Please correct the errors below.'))
        return super().form_invalid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Change Password')
        return context


class AllAuthPasswordSetView(AllAuthPasswordSetView):
    """
    Custom password set view for users without passwords (social auth)
    """
    form_class = AllAuthCompatibleSetPasswordForm
    template_name = 'password_set.html'
    
    def get_success_url(self):
        messages.success(self.request, _('Password set successfully!'))
        return reverse_lazy('users_profile')


class UserProfileView(LoginRequiredMixin, DetailView):
    """View for users to see their own profile"""
    model = User
    template_name = 'account/user_profile.html'
    context_object_name = 'user'
    
    def get_object(self):
        return self.request.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = getattr(self.request.user, 'profile', None)
        context['page_title'] = _('My Profile')
        
        # Check if user has a password set (for social auth users)
        context['has_password'] = self.request.user.has_usable_password()
        
        return context


class UserProfileUpdateView(LoginRequiredMixin, UpdateView):
    """View for users to edit their personal information"""
    model = User
    form_class = UserProfileForm
    template_name = 'account/user_profile_edit.html'
    
    def get_object(self):
        return self.request.user
    
    def get_success_url(self):
        messages.success(self.request, _('Profile updated successfully!'))
        return reverse_lazy('users_profile')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = _('Edit Profile')
        return context


# URL names for All Auth compatibility
class AllAuthCompatibleViews:
    """
    Mixin to provide All Auth compatible URL names
    """
    def get_success_url(self):
        # Use All Auth's default success URL or custom one
        return getattr(self, 'success_url', reverse_lazy('users_profile'))
    



class AvatarUploadView(LoginRequiredMixin, UpdateView):
    """Handle avatar upload"""
    model = User
    form_class = UserAvatarForm
    template_name = 'account/avatar_upload.html'
    
    def get_object(self):
        return self.request.user
    
    def form_valid(self, form):
        form.save()
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'avatar_url': self.object.avatar.url,
                'message': 'Avatar uploaded successfully!'
            })
        messages.success(self.request, 'Avatar uploaded successfully!')
        return redirect('users_profile')
    
    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'errors': form.errors,
                'message': 'Error uploading avatar.'
            })
        messages.error(self.request, 'Error uploading avatar.')
        return redirect('users_profile_edit')

class AvatarRemoveView(LoginRequiredMixin, TemplateView):
    """Handle avatar removal"""
    
    def post(self, request, *args, **kwargs):
        user = request.user
        if user.avatar:
            user.avatar.delete(save=False)
            user.avatar = None
            user.save()
            
            messages.success(request, 'Avatar removed successfully!')
        else:
            messages.info(request, 'No avatar to remove.')
        
        return redirect('users_profile_edit')