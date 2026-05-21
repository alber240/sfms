"""
SFMS Middleware - License Check
Developed by Albert A. Allen - allen.tech.africa@gmail.com
"""

from django.shortcuts import render
from django.urls import reverse
from .license_check import check_license

class LicenseCheckMiddleware:
    """
    This middleware checks the license on EVERY page request.
    If license is invalid, it shows an error page instead of the requested page.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Skip license check for these paths (so school can still see error page)
        skip_paths = [
            '/admin/',
            '/license-error/',
            '/static/',
            '/media/',
            '/logout/',
        ]
        
        # Check if current path should be skipped
        current_path = request.path
        should_skip = any(current_path.startswith(path) for path in skip_paths)
        
        if not should_skip:
            license_status = check_license()
            
            if not license_status.get('valid', False):
                # Show license error page
                return render(request, 'license_error.html', {
                    'error': license_status.get('error', 'License validation failed.'),
                    'school_name': license_status.get('school_name', 'Unknown'),
                    'developer_email': 'allen.tech.africa@gmail.com',
                    'developer_phone': '+250 790 362 843'
                }, status=403)
        
        response = self.get_response(request)
        return response