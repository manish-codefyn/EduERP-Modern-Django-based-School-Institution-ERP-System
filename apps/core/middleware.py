class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(':')[0]
        subdomain = host.split('.')[0]
        
        school_slug = request.headers.get('X-School-Slug', subdomain)
        
        try:
            from apps.organization.models import School
            school = School.objects.get(slug=school_slug, is_active=True)
            request.school = school
        except School.DoesNotExist:
            if not request.path.startswith('/admin/'):
                from django.http import HttpResponseForbidden
                return HttpResponseForbidden("School not found or inactive")
        
        response = self.get_response(request)
        return response
    
    
class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # You can later add logging of requests here
        response = self.get_response(request)
        return response