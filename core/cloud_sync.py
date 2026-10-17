"""
SFMS Cloud Sync Module
Syncs local data to Supabase cloud
"""

import json
import os
import requests
from datetime import datetime
from decimal import Decimal
from django.conf import settings


class CloudSync:
    """Handle cloud sync operations with Supabase"""
    
    def __init__(self):
        self.license_data = self._load_license()
        self.supabase_url = self.license_data.get('supabase_url', '')
        self.supabase_key = self.license_data.get('supabase_key', '')
        self.school_name = self.license_data.get('school_name', 'Unknown')
        self.recovery_key = self.license_data.get('recovery_key', '')
    
    def _load_license(self):
        """Load license data from file"""
        license_path = os.path.join(settings.BASE_DIR, 'license.json')
        try:
            with open(license_path, 'r') as f:
                return json.load(f)
        except:
            return {}
    
    def is_configured(self):
        """Check if Supabase is configured"""
        return bool(self.supabase_url and self.supabase_key)
    
    def _get_headers(self):
        """Get headers for Supabase API"""
        return {
            'apikey': self.supabase_key,
            'Authorization': f'Bearer {self.supabase_key}',
            'Content-Type': 'application/json',
            'Prefer': 'resolution=merge-duplicates'
        }
    
    def _test_connection(self):
        """Test connection to Supabase"""
        if not self.is_configured():
            return False, "Supabase not configured"
        
        try:
            response = requests.get(
                f"{self.supabase_url}/rest/v1/school_recovery?recovery_key=eq.{self.recovery_key}",
                headers=self._get_headers(),
                timeout=10
            )
            if response.status_code == 200:
                return True, "Connected"
            else:
                return False, f"Status: {response.status_code}"
        except Exception as e:
            return False, str(e)
    
    def sync_students(self):
        """Sync students to cloud"""
        from students.models import Student
        
        if not self.is_configured():
            return 0, "Not configured"
        
        students = Student.objects.filter(is_active=True)
        count = 0
        
        for student in students:
            data = {
                'id': student.id,
                'admission_number': student.admission_number,
                'first_name': student.first_name,
                'last_name': student.last_name,
                'class_name': student.get_class_name() if hasattr(student, 'get_class_name') else '',
                'student_type': student.student_type,
                'parent_name': student.parent_name or '',
                'parent_phone': student.parent_phone or '',
                'is_active': student.is_active,
                'synced_at': datetime.now().isoformat()
            }
            
            try:
                response = requests.post(
                    f"{self.supabase_url}/rest/v1/students",
                    headers=self._get_headers(),
                    json=data,
                    timeout=10
                )
                if response.status_code in [200, 201]:
                    count += 1
            except:
                pass
        
        return count, "Students synced"
    
    def sync_receipts(self):
        """Sync receipts to cloud"""
        from receipts.models import Receipt
        
        if not self.is_configured():
            return 0, "Not configured"
        
        receipts = Receipt.objects.filter(is_voided=False)
        count = 0
        
        for receipt in receipts:
            data = {
                'id': receipt.id,
                'receipt_number': receipt.receipt_number,
                'student_id': receipt.student.id,
                'student_name': receipt.student.full_name,
                'amount_lrd': float(receipt.amount_lrd),
                'amount_usd': float(receipt.amount_usd),
                'payment_date': receipt.payment_date.isoformat(),
                'payment_method': receipt.payment_method,
                'payment_period': receipt.payment_period,
                'academic_year': receipt.academic_year,
                'is_voided': receipt.is_voided,
                'synced_at': datetime.now().isoformat()
            }
            
            try:
                response = requests.post(
                    f"{self.supabase_url}/rest/v1/receipts",
                    headers=self._get_headers(),
                    json=data,
                    timeout=10
                )
                if response.status_code in [200, 201]:
                    count += 1
            except:
                pass
        
        return count, "Receipts synced"
    
    def sync_expenses(self):
        """Sync expenses to cloud"""
        from expenses.models import Expense
        
        if not self.is_configured():
            return 0, "Not configured"
        
        expenses = Expense.objects.all()
        count = 0
        
        for expense in expenses:
            data = {
                'id': expense.id,
                'category': expense.category.name,
                'description': expense.description,
                'amount_lrd': float(expense.amount_lrd),
                'amount_usd': float(expense.amount_usd),
                'expense_date': expense.expense_date.isoformat(),
                'academic_year': expense.academic_year,
                'synced_at': datetime.now().isoformat()
            }
            
            try:
                response = requests.post(
                    f"{self.supabase_url}/rest/v1/expenses",
                    headers=self._get_headers(),
                    json=data,
                    timeout=10
                )
                if response.status_code in [200, 201]:
                    count += 1
            except:
                pass
        
        return count, "Expenses synced"
    
    def sync_recovery_info(self):
        """Register recovery info in cloud"""
        if not self.is_configured():
            return 0, "Not configured"
        
        data = {
            'recovery_key': self.recovery_key,
            'school_name': self.school_name,
            'license_key': self.license_data.get('license_key', ''),
            'supabase_url': self.supabase_url,
            'last_sync': datetime.now().isoformat()
        }
        
        try:
            response = requests.post(
                f"{self.supabase_url}/rest/v1/school_recovery",
                headers=self._get_headers(),
                json=data,
                timeout=10
            )
            if response.status_code in [200, 201]:
                return 1, "Recovery info registered"
        except:
            pass
        
        return 0, "Recovery info failed"
    
    def sync_all(self):
        """Sync everything to cloud"""
        results = {
            'students': self.sync_students(),
            'receipts': self.sync_receipts(),
            'expenses': self.sync_expenses(),
            'recovery': self.sync_recovery_info(),
        }
        return results


def sync_to_cloud():
    """Convenience function to sync all data"""
    sync = CloudSync()
    if not sync.is_configured():
        return False, "Cloud sync not configured"
    
    results = sync.sync_all()
    return True, results