# apps/finance/utils.py

from django.contrib import messages


def get_user_institution(user, request=None):
    """
    Get institution from user profile or student profile.
    If request is provided, add an error message when not found.
    """
    # Check user profile
    if hasattr(user, 'profile') and getattr(user.profile, 'institution', None):
        return user.profile.institution

    # Check student profile
    student_profile = getattr(user, 'student_profile', None)
    if student_profile and getattr(student_profile, 'institution', None):
        return student_profile.institution

    # Optionally show error if request is provided
    if request:
        messages.error(request, "Your account is not linked to a school/institution.")

    return None