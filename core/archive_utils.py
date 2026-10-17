"""
SFMS Archive System
Archives academic years older than 5 years
"""

import os
import json
import zipfile
from datetime import datetime
from decimal import Decimal
from django.conf import settings
from django.utils import timezone


ARCHIVE_DIR = os.path.join(settings.BASE_DIR, 'archive')
RETENTION_YEARS = 5  # Keep 5 years in main database


class Archiver:
    """Handle archiving of old academic years"""
    
    def __init__(self):
        # Create archive directory if it doesn't exist
        if not os.path.exists(ARCHIVE_DIR):
            os.makedirs(ARCHIVE_DIR)
    
    def get_years_to_archive(self):
        """Get list of academic years that should be archived"""
        from fees.models import AcademicSession
        
        # Get all archived sessions
        sessions = AcademicSession.objects.filter(is_archived=True).order_by('academic_year')
        
        years_to_archive = []
        current_year = datetime.now().year
        
        for session in sessions:
            # Parse year (e.g., "2026/2027" or "2026-2027")
            try:
                year_str = session.academic_year.replace('/', '-')
                start_year = int(year_str.split('-')[0])
                
                # Check if older than retention period
                if (current_year - start_year) > RETENTION_YEARS:
                    # Check if not already archived
                    from .models import ArchiveIndex
                    if not ArchiveIndex.objects.filter(academic_year=session.academic_year).exists():
                        years_to_archive.append(session)
            except (ValueError, IndexError):
                continue
        
        return years_to_archive
    
    def archive_year(self, academic_year):
        """Archive a specific academic year"""
        from fees.models import AcademicSession, FeeStructure, StudentFeeLedger
        from students.models import Student, StudentYearStatus
        from receipts.models import Receipt, PaymentAllocation
        from expenses.models import Expense
        from payroll.models import PayrollEntry
        from .models import ArchiveIndex
        
        session = AcademicSession.objects.filter(academic_year=academic_year).first()
        if not session:
            return False, f"Academic year {academic_year} not found"
        
        # Create archive filename
        safe_year = academic_year.replace('/', '-')
        file_name = f"{safe_year}.zip"
        file_path = os.path.join(ARCHIVE_DIR, file_name)
        
        record_count = 0
        
        try:
            with zipfile.ZipFile(file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                
                # Archive students (year statuses)
                statuses = StudentYearStatus.objects.filter(academic_year=academic_year)
                statuses_data = []
                for status in statuses:
                    statuses_data.append({
                        'student_id': status.student.id,
                        'student_name': status.student.full_name,
                        'admission_number': status.student.admission_number,
                        'academic_year': status.academic_year,
                        'previous_class': status.previous_class.name if status.previous_class else None,
                        'new_class': status.new_class.name if status.new_class else None,
                        'status': status.status,
                        'previous_type': status.previous_type,
                        'new_type': status.new_type,
                        'notes': status.notes,
                    })
                    record_count += 1
                
                zipf.writestr('student_year_status.json', json.dumps(statuses_data, indent=2))
                
                # Archive receipts
                receipts = Receipt.objects.filter(academic_year=academic_year)
                receipts_data = []
                for receipt in receipts:
                    receipts_data.append({
                        'receipt_number': receipt.receipt_number,
                        'student_id': receipt.student.id,
                        'student_name': receipt.student.full_name,
                        'amount_lrd': str(receipt.amount_lrd),
                        'amount_usd': str(receipt.amount_usd),
                        'payment_date': receipt.payment_date.isoformat(),
                        'payment_method': receipt.payment_method,
                        'payment_period': receipt.payment_period,
                        'academic_year': receipt.academic_year,
                        'is_voided': receipt.is_voided,
                    })
                    record_count += 1
                
                zipf.writestr('receipts.json', json.dumps(receipts_data, indent=2))
                
                # Archive expenses
                expenses = Expense.objects.filter(academic_year=academic_year)
                expenses_data = []
                for expense in expenses:
                    expenses_data.append({
                        'category': expense.category.name,
                        'description': expense.description,
                        'amount_lrd': str(expense.amount_lrd),
                        'amount_usd': str(expense.amount_usd),
                        'expense_date': expense.expense_date.isoformat(),
                        'academic_year': expense.academic_year,
                        'notes': expense.notes,
                    })
                    record_count += 1
                
                zipf.writestr('expenses.json', json.dumps(expenses_data, indent=2))
                
                # Archive fee structures
                fee_structures = FeeStructure.objects.filter(academic_year=academic_year)
                fees_data = []
                for fs in fee_structures:
                    fees_data.append({
                        'class_name': fs.class_assigned.name,
                        'student_type': fs.student_type,
                        'category': fs.category.name,
                        'semester1_lrd': str(fs.semester1_amount_lrd),
                        'semester1_usd': str(fs.semester1_amount_usd),
                        'semester2_lrd': str(fs.semester2_amount_lrd),
                        'semester2_usd': str(fs.semester2_amount_usd),
                    })
                    record_count += 1
                
                zipf.writestr('fee_structures.json', json.dumps(fees_data, indent=2))
                
                # Archive student ledgers
                ledgers = StudentFeeLedger.objects.filter(academic_year=academic_year)
                ledgers_data = []
                for ledger in ledgers:
                    ledgers_data.append({
                        'student_id': ledger.student.id,
                        'student_name': ledger.student.full_name,
                        'academic_year': ledger.academic_year,
                        'semester1_total_lrd': str(ledger.semester1_total_lrd),
                        'semester1_paid_lrd': str(ledger.semester1_paid_lrd),
                        'semester2_total_lrd': str(ledger.semester2_total_lrd),
                        'semester2_paid_lrd': str(ledger.semester2_paid_lrd),
                        'discount_applied_lrd': str(ledger.discount_applied_lrd),
                    })
                    record_count += 1
                
                zipf.writestr('student_ledgers.json', json.dumps(ledgers_data, indent=2))
                
                # Archive metadata
                metadata = {
                    'academic_year': academic_year,
                    'session_name': session.name,
                    'start_date': session.start_date.isoformat(),
                    'end_date': session.end_date.isoformat(),
                    'archived_at': datetime.now().isoformat(),
                    'record_count': record_count,
                }
                zipf.writestr('metadata.json', json.dumps(metadata, indent=2))
            
            # Get file size
            file_size = os.path.getsize(file_path)
            
            # Create archive index
            ArchiveIndex.objects.create(
                academic_year=academic_year,
                file_name=file_name,
                file_size=file_size,
                record_count=record_count,
            )
            
            return True, f"Archived {academic_year} ({record_count} records)"
            
        except Exception as e:
            return False, f"Archive failed: {str(e)}"
    
    def archive_all_old_years(self):
        """Archive all years older than retention period"""
        years_to_archive = self.get_years_to_archive()
        results = []
        
        for session in years_to_archive:
            success, message = self.archive_year(session.academic_year)
            results.append({
                'year': session.academic_year,
                'success': success,
                'message': message,
            })
        
        return results


def run_auto_archive():
    """Run automatic archiving (called after year transition)"""
    archiver = Archiver()
    return archiver.archive_all_old_years()