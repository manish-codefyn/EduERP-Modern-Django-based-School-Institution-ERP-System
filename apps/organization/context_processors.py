from .models import Institution

def institution_context(request):
    """
    Add institution details (school/college) to all templates.
    """
    institution = None

    try:
        # Example: If multi-institution, you can filter by domain or session
        # For now, just fetch the first active one
        institution = Institution.objects.filter(is_active=True).first()
    except Institution.DoesNotExist:
        institution = None

    return {
        "institution": institution
    }
