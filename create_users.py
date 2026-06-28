"""
Create default users for SFMS
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sfms.settings')
django.setup()

from django.contrib.auth.models import User
from core.models import UserProfile

print("Creating default users...")

# Create accountant
accountant, created = User.objects.get_or_create(
    username='accountant',
    defaults={
        'email': '',
        'is_staff': True,
        'is_active': True
    }
)

if created:
    accountant.set_password('School2024')
    accountant.save()
    print("✅ Accountant created (password: School2024)")
else:
    print("ℹ️ Accountant already exists")

# Create principal
principal, created = User.objects.get_or_create(
    username='principal',
    defaults={
        'email': '',
        'is_staff': False,
        'is_active': True
    }
)

if created:
    principal.set_password('Principal2024')
    principal.save()
    print("✅ Principal created (password: Principal2024)")
else:
    print("ℹ️ Principal already exists")

print("\nDone!")