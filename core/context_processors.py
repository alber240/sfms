from .models import SchoolSetting
from .translations import translate

def school_settings(request):
    """Add school settings to all templates"""
    school_name = SchoolSetting.objects.filter(key='school_name').first()
    school_address = SchoolSetting.objects.filter(key='school_address').first()
    school_phone = SchoolSetting.objects.filter(key='school_phone').first()
    accountant_name = SchoolSetting.objects.filter(key='accountant_name').first()
    
    return {
        'school_name': school_name.value if school_name else 'SFMS SCHOOL',
        'school_address': school_address.value if school_address else '',
        'school_phone': school_phone.value if school_phone else '',
        'accountant_name': accountant_name.value if accountant_name else '',
    }

def user_language(request):
    """Simple language preference"""
    language = request.session.get('language', 'en')
    return {
        'LANGUAGE': language,
        'LANGUAGE_CODE': language,
        't': lambda text: translate(text, language)
    }
