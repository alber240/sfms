"""
SFMS Shared Utilities
Common functions used across the application.
"""

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Optional

from django.contrib import messages
from django.http import HttpRequest


def safe_decimal(value: any, default: Decimal = Decimal('0')) -> Decimal:
    """
    Safely convert a value to Decimal.
    
    Args:
        value: Value to convert (str, int, float)
        default: Default value if conversion fails
        
    Returns:
        Decimal value
    """
    if value is None or value == '':
        return default
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return default


def parse_date(date_str: str) -> Optional[datetime]:
    """
    Parse a date string in common formats.
    
    Args:
        date_str: Date string (YYYY-MM-DD, MM/DD/YYYY)
        
    Returns:
        datetime object or None
    """
    formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            continue
    
    return None


def format_currency(amount: Decimal, currency: str = 'LRD') -> str:
    """
    Format a decimal as currency string.
    
    Args:
        amount: Decimal amount
        currency: Currency code (LRD or USD)
        
    Returns:
        Formatted string (e.g., "1,500.00 LRD")
    """
    return f"{amount:,.2f} {currency}"


def get_client_ip(request: HttpRequest) -> str:
    """
    Get client IP address from request.
    
    Args:
        request: HTTP request
        
    Returns:
        IP address string
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    
    return ip


def is_principal(user) -> bool:
    """
    Check if user is a principal.
    
    Args:
        user: Django user object
        
    Returns:
        True if user is principal
    """
    return (
        user.username == 'principal' or 
        user.username.startswith('pri_')
    )


def is_accountant(user) -> bool:
    """
    Check if user is an accountant.
    
    Args:
        user: Django user object
        
    Returns:
        True if user is accountant
    """
    return not is_principal(user)