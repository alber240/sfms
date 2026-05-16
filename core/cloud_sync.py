import json
from datetime import datetime

class CloudSync:
    def __init__(self, supabase_url=None, supabase_key=None):
        self.supabase_url = supabase_url
        self.supabase_key = supabase_key
        self.client = None
        
        if supabase_url and supabase_key:
            try:
                # Try to import supabase
                try:
                    from supabase import create_client
                    self.client = create_client(supabase_url, supabase_key)
                except ImportError:
                    self.client = None
            except:
                self.client = None
    
    def is_configured(self):
        return self.client is not None
    
    def sync_students(self, students_data):
        if not self.is_configured():
            return False, "Cloud not configured"
        
        try:
            for student in students_data:
                self.client.table('students').upsert(student).execute()
            return True, f"Synced {len(students_data)} students"
        except Exception as e:
            return False, str(e)
    
    def sync_receipts(self, receipts_data):
        if not self.is_configured():
            return False, "Cloud not configured"
        
        try:
            for receipt in receipts_data:
                self.client.table('receipts').upsert(receipt).execute()
            return True, f"Synced {len(receipts_data)} receipts"
        except Exception as e:
            return False, str(e)
    
    def sync_expenses(self, expenses_data):
        if not self.is_configured():
            return False, "Cloud not configured"
        
        try:
            for expense in expenses_data:
                self.client.table('expenses').upsert(expense).execute()
            return True, f"Synced {len(expenses_data)} expenses"
        except Exception as e:
            return False, str(e)
    
    def get_students_from_cloud(self):
        if not self.is_configured():
            return None, "Cloud not configured"
        
        try:
            response = self.client.table('students').select('*').execute()
            return response.data, "Success"
        except Exception as e:
            return None, str(e)
    
    def sync_all(self, local_data):
        results = {}
        
        if 'students' in local_data:
            success, msg = self.sync_students(local_data['students'])
            results['students'] = {'success': success, 'message': msg}
        
        if 'receipts' in local_data:
            success, msg = self.sync_receipts(local_data['receipts'])
            results['receipts'] = {'success': success, 'message': msg}
        
        if 'expenses' in local_data:
            success, msg = self.sync_expenses(local_data['expenses'])
            results['expenses'] = {'success': success, 'message': msg}
        
        return results
