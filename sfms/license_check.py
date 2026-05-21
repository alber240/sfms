"""
SFMS License Management System
Developed by Albert A. Allen - allen.tech.africa@gmail.com
This module handles license validation for school installations.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from django.conf import settings

def check_license():
    """
    Check if the school has a valid license.
    Returns: dict with 'valid' (bool) and 'error' (str) or license data
    """
    
    # Path to license file (must be in the same directory as settings.py)
    license_path = os.path.join(settings.BASE_DIR, 'license.json')
    
    # Check if license file exists
    if not os.path.exists(license_path):
        return {
            'valid': False,
            'error': 'No license file found. Please contact Albert A. Allen at allen.tech.africa@gmail.com to activate SFMS.'
        }
    
    try:
        # Read the license file
        with open(license_path, 'r') as f:
            license_data = json.load(f)
        
        # Check required fields
        required_fields = ['school_name', 'license_key', 'expiry_date', 'developer']
        for field in required_fields:
            if field not in license_data:
                return {
                    'valid': False,
                    'error': f'License file is corrupted. Missing field: {field}. Please contact support at allen.tech.africa@gmail.com'
                }
        
        # Check if developer is correct
        if license_data.get('developer') != 'Albert A. Allen':
            return {
                'valid': False,
                'error': 'Invalid license. This license was not issued by Albert A. Allen. Please purchase a valid license at allen.tech.africa@gmail.com'
            }
        
        # Check if license has expired
        today = datetime.now().date()
        expiry_date = datetime.strptime(license_data['expiry_date'], '%Y-%m-%d').date()
        
        if today > expiry_date:
            return {
                'valid': False,
                'error': f'Your SFMS license expired on {license_data["expiry_date"]}. Please renew by contacting Albert A. Allen at allen.tech.africa@gmail.com',
                'school_name': license_data.get('school_name', 'Unknown')
            }
        
        # License is valid - return info for display
        return {
            'valid': True,
            'school_name': license_data.get('school_name', 'Licensed School'),
            'license_key': license_data.get('license_key', 'Unknown'),
            'expiry_date': license_data.get('expiry_date', 'Never'),
            'issued_date': license_data.get('issued_date', 'Unknown')
        }
        
    except json.JSONDecodeError:
        return {
            'valid': False,
            'error': 'License file is corrupted (invalid JSON). Please contact support at allen.tech.africa@gmail.com'
        }
    except Exception as e:
        return {
            'valid': False,
            'error': f'License check error: {str(e)}. Please contact Albert A. Allen at allen.tech.africa@gmail.com'
        }

def get_school_info():
    """Get school information from license file for display in footer"""
    license_path = os.path.join(settings.BASE_DIR, 'license.json')
    if os.path.exists(license_path):
        try:
            with open(license_path, 'r') as f:
                return json.load(f)
        except:
            pass
    
    # Return default info if no license
    return {
        'school_name': 'Unlicensed School - Contact Albert A. Allen',
        'license_key': 'NO LICENSE',
        'developer': 'Albert A. Allen',
        'developer_contact': 'allen.tech.africa@gmail.com'
    }

def is_license_valid():
    """Simple boolean check if license is valid"""
    result = check_license()
    return result.get('valid', False)