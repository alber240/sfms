from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser

class AuditMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.audit_user = None
        if hasattr(request, 'user') and not isinstance(request.user, AnonymousUser):
            request.audit_user = request.user
        request.audit_ip = self.get_client_ip(request)
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
