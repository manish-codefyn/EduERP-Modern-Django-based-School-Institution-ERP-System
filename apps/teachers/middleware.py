# middleware.py
from organization.models import Institution

class InstitutionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Example: store institution in session earlier during login
        inst_id = request.session.get("institution_id")
        request.institution = None
        if inst_id:
            try:
                request.institution = Institution.objects.get(id=inst_id)
            except Institution.DoesNotExist:
                pass
        return self.get_response(request)
