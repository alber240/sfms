"""
Create default users for SFMS - Simple version
Bypasses the UserProfile signal issue
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sfms.settings')
django.setup()

from django.contrib.auth.models import User
from django.db import connection

print("Creating default users...")

# Check if tables exist
with connection.cursor() as cursor:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='auth_user'")
    if not cursor.fetchone():
        print("❌ Database not ready. Run migrations first!")
        exit()

# Create accountant
try:
    user = User.objects.create_user(
        username='accountant',
        password='School2024',
        email='',
        is_staff=True,
        is_active=True
    )
    print("✅ Accountant created (password: School2024)")
except:
    print("ℹ️ Accountant already exists")

# Create principal
try:
    user = User.objects.create_user(
        username='principal',
        password='Principal2024',
        email='',
        is_staff=False,
        is_active=True
    )
    print("✅ Principal created (password: Principal2024)")
except:
    print("ℹ️ Principal already exists")

print("\nDone!")
