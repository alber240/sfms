import urllib.parse
import re

# ============================================================
# COUNTRY CONFIGURATION - LIBERIA
# ============================================================
COUNTRY_CODE = '231'  # Liberia
PHONE_LENGTH = 9  # Liberia has 9 digits after country code (e.g., 77900234)

def format_phone_number(phone_number):
    """
    Format Liberian phone numbers to international format (+231)
    
    Examples:
    077900234 → 23177900234
    0779 00234 → 23177900234
    23177900234 → 23177900234
    +23177900234 → 23177900234
    77900234 → 23177900234
    """
    if not phone_number:
        return None
    
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', str(phone_number))
    
    # Remove leading country code if already present
    if digits.startswith(COUNTRY_CODE):
        digits = digits[len(COUNTRY_CODE):]
    
    # Remove leading '0' if present (Liberian numbers often start with 0)
    if digits.startswith('0'):
        digits = digits[1:]
    
    # Ensure we have the correct number of digits (Liberia has 9 digits after 231)
    if len(digits) == PHONE_LENGTH:
        formatted = COUNTRY_CODE + digits
    elif len(digits) == PHONE_LENGTH + len(COUNTRY_CODE):
        formatted = digits
    else:
        # If format is unknown, return original
        return phone_number
    
    return formatted

def generate_whatsapp_link(phone_number, message):
    """Generate WhatsApp click-to-chat link with proper formatting"""
    formatted_phone = format_phone_number(phone_number)
    
    if not formatted_phone:
        return None
    
    encoded_message = urllib.parse.quote(message)
    return f"https://wa.me/{formatted_phone}?text={encoded_message}"

def generate_default_reminder(student_name, due_amount, due_date, school_name):
    """Generate default reminder message"""
    formatted_amount = f"{due_amount:,.0f}"
    
    return f"""📚 SCHOOL FEE REMINDER

Dear Parent,

This is a friendly reminder from {school_name}.

Student: {student_name}
Amount Due: {formatted_amount} LRD
Due Date: {due_date}

Please ensure your child's school fees are paid on time.

Thank you for your cooperation.

{school_name} Administration
📍 Monrovia, Liberia"""

def generate_overdue_message(student_name, overdue_amount, days_overdue, school_name):
    """Generate overdue payment message"""
    formatted_amount = f"{overdue_amount:,.0f}"
    
    return f"""⚠️ URGENT: SCHOOL FEES OVERDUE ⚠️

Dear Parent,

Student: {student_name}
Overdue Amount: {formatted_amount} LRD
Days Overdue: {days_overdue}

Your child's school fees are now past due.

Please make payment immediately to avoid disruption of your child's education.

Thank you for your prompt attention.

{school_name} Administration
📍 Monrovia, Liberia"""

def validate_phone_number(phone_number):
    """Check if a phone number is valid for Liberia"""
    formatted = format_phone_number(phone_number)
    if formatted and formatted.startswith(COUNTRY_CODE) and len(formatted) == len(COUNTRY_CODE) + PHONE_LENGTH:
        return True, formatted
    return False, None