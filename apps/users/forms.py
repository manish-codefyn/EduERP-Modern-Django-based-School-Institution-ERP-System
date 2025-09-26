# core/forms.py
from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from allauth.account.forms import ChangePasswordForm as AllAuthChangePasswordForm
from allauth.account import app_settings as allauth_account_settings
from allauth.account.adapter import get_adapter
from .models import User, UserProfile

class AllAuthCompatibleSecurityForm(AllAuthChangePasswordForm):
    """
    Django All Auth compatible password change form with enhanced validation
    and Bootstrap styling.
    """
    
    # Add confirm new password field for better UX (not in original All Auth form)
    confirm_new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Confirm your new password'),
            'autocomplete': 'new-password'
        }),
        label=_('Confirm New Password'),
        strip=False,
        required=True
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Update All Auth form fields with Bootstrap styling
        self.fields['oldpassword'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': _('Enter your current password'),
            'autocomplete': 'current-password'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': _('Enter your new password'),
            'autocomplete': 'new-password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': _('Confirm your new password'),
            'autocomplete': 'new-password'
        })
        
        # Update labels to be more user-friendly
        self.fields['oldpassword'].label = _('Current Password')
        self.fields['password1'].label = _('New Password')
        self.fields['password2'].label = _('New Password Confirmation')
        
        # Custom help text for password requirements
        if allauth_account_settings.PASSWORD_MIN_LENGTH:
            min_length = allauth_account_settings.PASSWORD_MIN_LENGTH
            self.fields['password1'].help_text = _(
                f'Your password must contain at least {min_length} characters. '
                'Avoid using common words or personal information.'
            )
    
    def clean_oldpassword(self):
        """Custom validation for old password"""
        old_password = self.cleaned_data.get('oldpassword')
        if not self.user.check_password(old_password):
            raise ValidationError(_('Your current password was entered incorrectly. Please enter it again.'))
        return old_password
    
    def clean_password1(self):
        """Validate new password strength using All Auth's validation"""
        password1 = self.cleaned_data.get('password1')
        
        if password1:
            # Check if new password is the same as old password
            if self.user.check_password(password1):
                raise ValidationError(_('New password must be different from your current password.'))
            
            # Use All Auth's password validation
            try:
                get_adapter().clean_password(password1, user=self.user)
            except ValidationError as e:
                raise ValidationError(e.messages)
        
        return password1
    
    def clean_password2(self):
        """Validate that new passwords match"""
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        confirm_password = self.cleaned_data.get('confirm_new_password')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError(_('The two new password fields didn\'t match.'))
        
        if password2 and confirm_password and password2 != confirm_password:
            raise ValidationError(_('The new password and confirmation password didn\'t match.'))
        
        return password2
    
    def clean(self):
        """Additional cross-field validation"""
        cleaned_data = super().clean()
        
        # Check if new password is too similar to user information
        new_password = cleaned_data.get('password1')
        if new_password:
            user_info = [
                self.user.email,
                self.user.first_name,
                self.user.last_name,
            ]
            
            # Remove None values
            user_info = [info for info in user_info if info]
            
            for info in user_info:
                if info and info.lower() in new_password.lower():
                    self.add_error(
                        'password1',
                        _('Your password cannot contain your email or name.')
                    )
                    break
        
        return cleaned_data
    
    def save(self):
        """Save the new password using All Auth's method"""
        # Call All Auth's save method which handles password change
        # and any additional All Auth functionality (like signals)
        return super().save()


class AllAuthCompatibleSetPasswordForm(forms.Form):
    """
    Form for setting password when user doesn't have one (social auth users)
    Compatible with All Auth's SetPasswordForm
    """
    
    password1 = forms.CharField(
        label=_("New Password"),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your new password'),
            'autocomplete': 'new-password'
        }),
        strip=False,
    )
    
    password2 = forms.CharField(
        label=_("New Password (again)"),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Confirm your new password'),
            'autocomplete': 'new-password'
        }),
        strip=False,
    )
    
    confirm_new_password = forms.CharField(
        label=_("Confirm New Password"),
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': _('Confirm your new password'),
            'autocomplete': 'new-password'
        }),
        strip=False,
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        confirm_password = self.cleaned_data.get("confirm_new_password")
        
        if password1 and password2 and password1 != password2:
            raise ValidationError(_("The two password fields didn't match."))
        
        if password2 and confirm_password and password2 != confirm_password:
            raise ValidationError(_("The new password and confirmation password didn't match."))
        
        return password2
    
    def clean_password1(self):
        password1 = self.cleaned_data.get("password1")
        
        if password1:
            # Use All Auth's password validation
            try:
                get_adapter().clean_password(password1, user=self.user)
            except ValidationError as e:
                raise ValidationError(e.messages)
        
        return password1
    
    def save(self, commit=True):
        password = self.cleaned_data["password1"]
        self.user.set_password(password)
        if commit:
            self.user.save()
        return self.user


class AllAuthPasswordResetForm(forms.Form):
    """
    Custom password reset form compatible with All Auth
    """
    
    email = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('Enter your email address'),
            'autocomplete': 'email'
        }),
        max_length=254,
    )
    
    def clean_email(self):
        email = self.cleaned_data["email"]
        email = get_adapter().clean_email(email)
        return email


# Maintain backward compatibility with your original form names
UserSecurityForm = AllAuthCompatibleSecurityForm


class UserProfileForm(forms.ModelForm):
    """Form for updating user profile information (compatible with All Auth)"""
    
    # Additional fields from UserProfile
    address = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': _('Enter your complete address')
        }),
        required=False,
        label=_('Address'),
        max_length=500
    )
    
    secondary_email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _('secondary@example.com')
        }),
        required=False,
        label=_('Secondary Email')
    )
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'phone', 
            'date_of_birth', 'avatar'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'avatar': forms.FileInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make email and names required
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['email'].required = True
        
        # Populate with profile data if exists
        if self.instance and hasattr(self.instance, 'profile'):
            profile = self.instance.profile
            self.fields['address'].initial = profile.address
            self.fields['secondary_email'].initial = profile.secondary_email
    
    def clean_email(self):
        """Validate that email is unique excluding current user"""
        email = self.cleaned_data.get('email')
        if email:
            # Use All Auth's email validation
            email = get_adapter().clean_email(email)
            
            queryset = User.objects.filter(email=email)
            if self.instance and self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            
            if queryset.exists():
                raise ValidationError(_('A user with this email already exists.'))
        return email
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        if commit:
            user.save()
            
            # Update or create UserProfile
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.address = self.cleaned_data['address']
            profile.secondary_email = self.cleaned_data['secondary_email']
            profile.save()
        
        return user
    


class UserAvatarForm(forms.ModelForm):
    """Form specifically for avatar upload"""
    
    avatar = forms.ImageField(
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': 'image/*'
        }),
        label=_('Profile Picture'),
        help_text=_('JPG, PNG or GIF. Max 2MB.')
    )
    
    class Meta:
        model = User
        fields = ['avatar']
    
    def clean_avatar(self):
        """Validate avatar file"""
        avatar = self.cleaned_data.get('avatar')
        
        if avatar:
            # Check file size (2MB limit)
            if avatar.size > 2 * 1024 * 1024:
                raise ValidationError(_('Image file too large ( > 2MB ).'))
            
            # Check file type
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
            import os
            ext = os.path.splitext(avatar.name)[1].lower()
            if ext not in valid_extensions:
                raise ValidationError(_('Unsupported file extension. Supported: JPG, PNG, GIF, WebP.'))
            
            # Check image dimensions (optional)
            from PIL import Image
            try:
                img = Image.open(avatar)
                if img.size[0] > 2000 or img.size[1] > 2000:
                    raise ValidationError(_('Image dimensions too large. Maximum 2000x2000 pixels.'))
            except Exception:
                raise ValidationError(_('Invalid image file.'))
        
        return avatar
