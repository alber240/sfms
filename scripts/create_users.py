import sys
import os
import django
import random
import string

# Setup Django
sys.path.append('C:\\SFMS')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sfms.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()

def generate_temp_password():
    """Generate a temporary password"""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=10))

def create_unique_users(school_code):
    """Create unique users for a school"""
    
    # Accountant user
    accountant_username = f"acc_{school_code}"
    accountant_temp_password = generate_temp_password()
    
    # Principal user
    principal_username = f"pri_{school_code}"
    principal_temp_password = generate_temp_password()
    
    # Create or update users
    accountant, created = User.objects.get_or_create(
        username=accountant_username,
        defaults={
            'email': f"{accountant_username}@school.com",
            'is_staff': True,
            'is_superuser': True
        }
    )
    accountant.set_password(accountant_temp_password)
    accountant.save()
    
    principal, created = User.objects.get_or_create(
        username=principal_username,
        defaults={
            'email': f"{principal_username}@school.com",
            'is_staff': False,
            'is_superuser': False
        }
    )
    principal.set_password(principal_temp_password)
    principal.save()
    
    # Create file with credentials
    with open('school_credentials.txt', 'w') as f:
        f.write("=" * 50 + "\n")
        f.write("YOUR SFMS LOGIN CREDENTIALS\n")
        f.write("=" * 50 + "\n\n")
        f.write("IMPORTANT: You will be asked to change your password on first login!\n\n")
        f.write(f"ACCOUNTANT LOGIN:\n")
        f.write(f"  Username: {accountant_username}\n")
        f.write(f"  Temporary Password: {accountant_temp_password}\n\n")
        f.write(f"PRINCIPAL LOGIN:\n")
        f.write(f"  Username: {principal_username}\n")
        f.write(f"  Temporary Password: {principal_temp_password}\n\n")
        f.write("=" * 50 + "\n")
        f.write("Please change your password immediately after login.\n")
        f.write("Keep these credentials safe!\n")
    
    print(f"✅ Created accountant: {accountant_username}")
    print(f"✅ Created principal: {principal_username}")
    print(f"📄 Credentials saved to school_credentials.txt")
    return accountant_username, principal_username

if __name__ == "__main__":
    school_code = input("Enter school code (e.g., MON001): ")
    create_unique_users(school_code)