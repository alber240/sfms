"""
Run this script ONCE during school installation to create unique users
Usage: python create_school_users.py
"""

import sys
import os
import random
import string
from datetime import datetime

# Setup Django
sys.path.append('C:\\SFMS')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sfms.settings')

import django
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()
from core.models import UserProfile

def generate_temp_password():
    """Generate a secure temporary password"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=12))

def generate_school_code():
    """Generate unique school code"""
    year = datetime.now().year
    random_num = random.randint(100, 999)
    return f"{year}{random_num}"

def create_school_users():
    print("=" * 60)
    print("SFMS SCHOOL USER SETUP")
    print("=" * 60)
    print()
    
    school_name = input("Enter School Name: ").strip().upper().replace(" ", "_")
    school_code = generate_school_code()
    
    # Create unique usernames
    accountant_username = f"acc_{school_name}_{school_code}"
    principal_username = f"pri_{school_name}_{school_code}"
    
    # Generate temporary passwords
    accountant_temp = generate_temp_password()
    principal_temp = generate_temp_password()
    
    print()
    print("Creating users...")
    
    # Create Accountant (full access)
    accountant, created = User.objects.get_or_create(
        username=accountant_username,
        defaults={
            'email': f"{accountant_username}@school.com",
            'is_staff': True,
            'is_superuser': True
        }
    )
    accountant.set_password(accountant_temp)
    accountant.save()
    
    # Create or update profile (FIXED: use update_or_create instead of get_or_create)
    profile, created = UserProfile.objects.update_or_create(
        user=accountant,
        defaults={
            'require_password_change': True,
            'school_code': school_code
        }
    )
    
    # Create Principal (read-only)
    principal, created = User.objects.get_or_create(
        username=principal_username,
        defaults={
            'email': f"{principal_username}@school.com",
            'is_staff': False,
            'is_superuser': False
        }
    )
    principal.set_password(principal_temp)
    principal.save()
    
    # Create or update profile
    profile, created = UserProfile.objects.update_or_create(
        user=principal,
        defaults={
            'require_password_change': True,
            'school_code': school_code
        }
    )
    
    # Save credentials to file on desktop
    desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
    filename = os.path.join(desktop, f"SFMS_CREDENTIALS_{school_name}_{school_code}.txt")
    
    with open(filename, 'w') as f:
        f.write("=" * 60 + "\n")
        f.write("SFMS LOGIN CREDENTIALS\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"School: {school_name}\n")
        f.write(f"School Code: {school_code}\n")
        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("=" * 60 + "\n")
        f.write("ACCOUNTANT LOGIN (Full Access)\n")
        f.write("=" * 60 + "\n")
        f.write(f"Username: {accountant_username}\n")
        f.write(f"Temporary Password: {accountant_temp}\n\n")
        f.write("=" * 60 + "\n")
        f.write("PRINCIPAL LOGIN (Read Only)\n")
        f.write("=" * 60 + "\n")
        f.write(f"Username: {principal_username}\n")
        f.write(f"Temporary Password: {principal_temp}\n\n")
        f.write("=" * 60 + "\n")
        f.write("IMPORTANT:\n")
        f.write("- You will be asked to change your password on first login\n")
        f.write("- Keep these credentials safe\n")
        f.write("- Do not share your password with anyone\n")
        f.write("=" * 60 + "\n")
    
    print()
    print("=" * 60)
    print("USERS CREATED SUCCESSFULLY!")
    print("=" * 60)
    print(f"Accountant: {accountant_username}")
    print(f"Principal: {principal_username}")
    print()
    print(f"Credentials saved to: {filename}")
    print()
    print("Give this file to the school administrator!")
    print("=" * 60)
    
    return accountant_username, principal_username

if __name__ == "__main__":
    create_school_users()