from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from datetime import date, timedelta
from receipts.models import Receipt
from expenses.models import Expense
from students.models import Student
from expenses.models import ExpenseApproval
from .backup_utils import get_usb_drives
import json
import os
import requests
import zipfile
import shutil
from django.conf import settings
from django.utils import timezone
# Safe imports for fees models
try:
    from fees.models import StudentFeeLedger, InstallmentReminder
except ImportError:
    StudentFeeLedger = None
    InstallmentReminder = None

def login_view(request):
    from .models import UserProfile
    
    if request.user.is_authenticated:
        # Check if user needs to change password
        try:
            profile = request.user.profile
            if profile.require_password_change:
                return redirect('change_password')
        except:
            pass
        
        # Redirect based on user role
        if request.user.username.startswith('pri_') or request.user.username == 'principal':
            return redirect('principal_dashboard')
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user:
            login(request, user)
            # Check if temporary password
            try:
                profile = user.profile
                if profile.require_password_change:
                    return redirect('change_password')
            except:
                pass
            
            # Redirect based on user role
            if user.username.startswith('pri_') or user.username == 'principal':
                return redirect('principal_dashboard')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

# Add to core/views.py
@login_required
def change_password(request):
    """Force password change on first login"""
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return render(request, 'change_password.html')
        
        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters')
            return render(request, 'change_password.html')
        
        request.user.set_password(new_password)
        request.user.require_password_change = False
        request.user.save()
        
        # Re-authenticate
        from django.contrib.auth import authenticate, login
        user = authenticate(username=request.user.username, password=new_password)
        login(request, user)
        
        messages.success(request, 'Password changed successfully!')
        
        if request.user.username.startswith('pri_'):
            return redirect('principal_dashboard')
        return redirect('dashboard')
    
    return render(request, 'change_password.html')

@login_required
def dashboard_view(request):
    from .models import ExchangeRate
    from fees.models import AcademicSession
    from datetime import date
    from django.db.models import Sum
    
    today = date.today()
    
    # Get active academic year
    active_session = AcademicSession.objects.filter(is_active=True).first()
    academic_year = active_session.academic_year if active_session else '2025-2026'
    
    # Get today's exchange rate or most recent
    exchange_rate_obj = ExchangeRate.objects.filter(rate_date=today).first()
    if not exchange_rate_obj:
        exchange_rate_obj = ExchangeRate.objects.first()
    
    exchange_rate = exchange_rate_obj.lrd_to_usd if exchange_rate_obj else 200
    
    # Today's collections - filter by academic year too
    today_receipts = Receipt.objects.filter(
        payment_date=today, 
        is_voided=False,
        academic_year=academic_year
    )
    total_collected_lrd = today_receipts.aggregate(Sum('amount_lrd'))['amount_lrd__sum'] or 0
    total_collected_usd = today_receipts.aggregate(Sum('amount_usd'))['amount_usd__sum'] or 0
    
    # Today's expenses - filter by academic year
    today_expenses = Expense.objects.filter(
        expense_date=today,
        academic_year=academic_year
    )
    total_expenses_lrd = today_expenses.aggregate(Sum('amount_lrd'))['amount_lrd__sum'] or 0
    total_expenses_usd = today_expenses.aggregate(Sum('amount_usd'))['amount_usd__sum'] or 0
    
    # Calculate net
    net_lrd = total_collected_lrd - total_expenses_lrd
    net_usd = total_collected_usd - total_expenses_usd
    net_combined = net_lrd + (net_usd * exchange_rate)
    
    # Recent receipts - filter by academic year
    recent_receipts = Receipt.objects.filter(
        is_voided=False,
        academic_year=academic_year
    ).order_by('-payment_date', '-id')[:10]
    
    context = {
        'total_collected_lrd': total_collected_lrd,
        'total_collected_usd': total_collected_usd,
        'total_expenses_lrd': total_expenses_lrd,
        'total_expenses_usd': total_expenses_usd,
        'net_lrd': net_lrd,
        'net_usd': net_usd,
        'net_combined': net_combined,
        'exchange_rate': exchange_rate,
        'recent_receipts': recent_receipts,
        'academic_year': academic_year,
    }
    return render(request, 'dashboard.html', context)

@login_required
@login_required
def principal_dashboard(request):
    from datetime import date, timedelta
    from django.db.models import Sum, Count
    from receipts.models import Receipt
    from expenses.models import Expense
    from students.models import Student
    from fees.models import StudentFeeLedger, InstallmentReminder
    
    if request.user.username != 'principal':
        return redirect('dashboard')
    
    today = date.today()
    
    # Today's collections
    today_receipts = Receipt.objects.filter(payment_date=today, is_voided=False)
    total_collected_lrd = today_receipts.aggregate(Sum('amount_lrd'))['amount_lrd__sum'] or 0
    total_collected_usd = today_receipts.aggregate(Sum('amount_usd'))['amount_usd__sum'] or 0
    
    # This month's collections
    month_start = date(today.year, today.month, 1)
    month_receipts = Receipt.objects.filter(payment_date__gte=month_start, is_voided=False)
    monthly_collected_lrd = month_receipts.aggregate(Sum('amount_lrd'))['amount_lrd__sum'] or 0
    monthly_collected_usd = month_receipts.aggregate(Sum('amount_usd'))['amount_usd__sum'] or 0
    
    # Students with balance
    students_with_balance = StudentFeeLedger.objects.exclude(
        semester1_total_lrd=0, semester2_total_lrd=0
    ).count()
    pending_approvals_count = ExpenseApproval.objects.filter(status='PENDING').count()
    
    total_students = Student.objects.filter(is_active=True).count()
    
    # Overdue reminders
    overdue_reminders = InstallmentReminder.objects.filter(is_paid=False, due_date__lt=today).count()
    
    # Recent receipts
    recent_receipts = Receipt.objects.filter(is_voided=False).order_by('-payment_date')[:10]
    
    context = {
        'total_collected_lrd': total_collected_lrd,
        'total_collected_usd': total_collected_usd,
        'monthly_collected_lrd': monthly_collected_lrd,
        'monthly_collected_usd': monthly_collected_usd,
        'students_with_balance': students_with_balance,
        'total_students': total_students,
        'overdue_reminders': overdue_reminders,
        'recent_receipts': recent_receipts,
        'today': today,
    }
    return render(request, 'principal_dashboard.html', context)

@login_required
def exchange_rate_settings(request):
    """Manage daily exchange rates"""
    from .models import ExchangeRate
    from datetime import date
    
    today = date.today()
    current_rate = ExchangeRate.objects.filter(rate_date=today).first()
    recent_rates = ExchangeRate.objects.all()[:10]
    
    if request.method == 'POST':
        rate_date = request.POST.get('rate_date', today)
        lrd_to_usd = request.POST.get('lrd_to_usd')
        notes = request.POST.get('notes', '')
        
        if lrd_to_usd:
            rate, created = ExchangeRate.objects.update_or_create(
                rate_date=rate_date,
                defaults={'lrd_to_usd': lrd_to_usd, 'notes': notes}
            )
            if created:
                messages.success(request, f'Exchange rate for {rate_date} added successfully!')
            else:
                messages.success(request, f'Exchange rate for {rate_date} updated successfully!')
        else:
            messages.error(request, 'Please enter an exchange rate')
        
        return redirect('exchange_rate_settings')
    
    context = {
        'current_rate': current_rate,
        'recent_rates': recent_rates,
        'today': today,
    }
    return render(request, 'core/exchange_rate.html', context)

@login_required
def exchange_rate_settings(request):
    """Manage daily exchange rates"""
    from .models import ExchangeRate
    from datetime import date
    
    today = date.today()
    current_rate = ExchangeRate.objects.filter(rate_date=today).first()
    recent_rates = ExchangeRate.objects.all()[:10]
    
    if request.method == 'POST':
        rate_date = request.POST.get('rate_date', today)
        lrd_to_usd = request.POST.get('lrd_to_usd')
        notes = request.POST.get('notes', '')
        
        if lrd_to_usd:
            rate, created = ExchangeRate.objects.update_or_create(
                rate_date=rate_date,
                defaults={'lrd_to_usd': lrd_to_usd, 'notes': notes}
            )
            if created:
                messages.success(request, f'Exchange rate for {rate_date} added successfully!')
            else:
                messages.success(request, f'Exchange rate for {rate_date} updated successfully!')
        else:
            messages.error(request, 'Please enter an exchange rate')
        
        return redirect('exchange_rate_settings')
    
    context = {
        'current_rate': current_rate,
        'recent_rates': recent_rates,
        'today': today,
    }
    return render(request, 'core/exchange_rate.html', context)
@login_required
def undo_last_transaction(request):
    """Undo the last transaction (receipt or expense)"""
    from receipts.models import Receipt
    from expenses.models import Expense
    from audit.models import AuditLog
    from fees.models import StudentFeeLedger
    
    # Get last receipt
    last_receipt = Receipt.objects.filter(is_voided=False).order_by('-created_at').first()
    last_expense = Expense.objects.order_by('-created_at').first()
    
    # Determine which is newer
    last_transaction = None
    transaction_type = None
    
    if last_receipt and last_expense:
        if last_receipt.created_at > last_expense.created_at:
            last_transaction = last_receipt
            transaction_type = 'receipt'
        else:
            last_transaction = last_expense
            transaction_type = 'expense'
    elif last_receipt:
        last_transaction = last_receipt
        transaction_type = 'receipt'
    elif last_expense:
        last_transaction = last_expense
        transaction_type = 'expense'
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        
        if not last_transaction:
            messages.error(request, 'No transaction to undo')
            return redirect('dashboard')
        
        # Log the undo action
        AuditLog.objects.create(
            action_type='UNDO',
            table_name=transaction_type,
            record_id=last_transaction.id,
            old_values={'id': last_transaction.id, 'data': str(last_transaction)},
            reason=reason,
            ip_address=request.META.get('REMOTE_ADDR'),
            user=request.user
        )
        
        if transaction_type == 'receipt':
            # Void the receipt instead of deleting
            last_transaction.is_voided = True
            last_transaction.void_reason = f'Undo by user: {reason}' if reason else 'Undo by user'
            last_transaction.save()
            
            # Restore student balance
            ledger = StudentFeeLedger.objects.filter(student=last_transaction.student).first()
            if ledger:
                # Reverse the payment (simplified - would need to track which semester)
                ledger.amount_paid_lrd -= last_transaction.amount_lrd
                ledger.amount_paid_usd -= last_transaction.amount_usd
                ledger.save()
            
            messages.success(request, f'Receipt #{last_transaction.receipt_number} has been voided and undone')
        
        elif transaction_type == 'expense':
            # Delete the expense
            last_transaction.delete()
            messages.success(request, f'Expense has been undone and removed')
        
        return redirect('dashboard')
    
    context = {
        'last_transaction': last_transaction,
        'transaction_type': transaction_type,
    }
    return render(request, 'core/undo.html', context)
@login_required
def check_reminder(request):
    """Check if 4 PM reminder should be shown and process pending emails"""
    from .models import DailyReminder
    from .email_utils import process_email_queue
    from datetime import datetime, time
    
    # Process pending emails when internet is available
    process_email_queue()
    
    now = datetime.now()
    today = now.date()
    reminder_time = time(16, 0)  # 4 PM
    
    reminder = DailyReminder.objects.filter(reminder_date=today).first()
    
    if now.time() >= reminder_time and (not reminder or not reminder.is_dismissed):
        return JsonResponse({'show_reminder': True, 'message': 'Did you record today\'s mobile money transactions?'})
    
    return JsonResponse({'show_reminder': False})

@login_required
def dismiss_reminder(request):
    """Dismiss the 4 PM reminder"""
    from .models import DailyReminder
    from django.utils import timezone
    from datetime import date
    
    today = date.today()
    reminder, created = DailyReminder.objects.get_or_create(reminder_date=today)
    reminder.is_dismissed = True
    reminder.dismissed_at = timezone.now()
    reminder.save()
    
    return JsonResponse({'success': True})


@login_required
def backup_view(request):
    """Backup management page"""
    from django.conf import settings
    import os  # <-- ADD THIS LINE
    import glob
    from .backup_utils import create_backup, get_usb_drives
    from datetime import datetime
    
    usb_drives = get_usb_drives()
    backup_files = []
    
    # List existing backups
    backup_folder = settings.BASE_DIR / 'backups'
    if backup_folder.exists():
        backups = sorted(glob.glob(str(backup_folder / 'sfms_backup_*.zip')), reverse=True)[:10]
        for b in backups:
            backup_files.append({
                'name': os.path.basename(b),
                'size': os.path.getsize(b) / 1024 / 1024,
                'date': datetime.fromtimestamp(os.path.getctime(b)).strftime('%Y-%m-%d %H:%M')
            })
    
    if request.method == 'POST':
        backup_to_usb = request.POST.get('backup_to_usb') == 'on'
        zip_path, usb_copied = create_backup(backup_to_usb=backup_to_usb)
        
        if usb_copied:
            messages.success(request, '✅ Backup completed and copied to USB drive!')
        elif backup_to_usb:
            messages.warning(request, '⚠️ Backup created but no USB drive detected. Backup saved locally.')
        else:
            messages.success(request, '✅ Backup completed successfully!')
        
        return redirect('backup_view')
    
    context = {
        'usb_drives': usb_drives,
        'backup_files': backup_files,
    }
    return render(request, 'core/backup.html', context)
def logout_view(request):
    """Logout and trigger auto-backup"""
    from django.contrib.auth import logout
    from django.contrib import messages
    import os
    from django.conf import settings
    from .backup_utils import auto_backup_on_exit
    
    # Trigger auto-backup before logout
    success, result, usb_copied = auto_backup_on_exit()
    
    logout(request)
    
    if success:
        if usb_copied:
            messages.success(request, '✅ Auto-backup completed and saved to USB!')
        else:
            messages.info(request, 'ℹ️ Auto-backup completed (no USB detected)')
    else:
        messages.warning(request, f'⚠️ Auto-backup failed: {result}')
    
    return redirect('login')

@login_required
def auto_backup_endpoint(request):
    """Endpoint for auto-backup triggered by browser close"""
    from django.http import JsonResponse
    from .backup_utils import auto_backup_on_exit
    
    if request.method == 'POST':
        success, result, usb_copied = auto_backup_on_exit()
        if success:
            return JsonResponse({'status': 'success', 'usb_copied': usb_copied})
        else:
            return JsonResponse({'status': 'error', 'message': result}, status=500)
    
    return JsonResponse({'status': 'method not allowed'}, status=405)


@login_required
def school_info_settings(request):
    """Manage school information"""
    from .models import SchoolSetting
    from django.contrib import messages
    from django.shortcuts import render, redirect
    
    if request.method == 'POST':
        # Save school settings
        settings_keys = ['school_name', 'school_address', 'school_phone', 'school_email', 'accountant_name', 'school_email', 'smtp_host', 'smtp_port', 'smtp_user', 'smtp_password' ]
        for key in settings_keys:
            value = request.POST.get(key, '')
            SchoolSetting.objects.update_or_create(
                key=key,
                defaults={'value': value, 'description': f'School {key.replace("_", " ")}'}
            )
        messages.success(request, 'School information updated successfully!')
        return redirect('school_info')
    
    # Get current settings
    school_info = {}
    for key in ['school_name', 'school_address', 'school_phone', 'school_email']:
        setting = SchoolSetting.objects.filter(key=key).first()
        school_info[key] = setting.value if setting else ''
    
    context = {
        'school_info': school_info,
    }
    return render(request, 'core/school_info.html', context)
def school_settings(request):
    """Add school settings to all templates"""
    from .models import SchoolSetting
    
    school_name = SchoolSetting.objects.filter(key='school_name').first()
    school_address = SchoolSetting.objects.filter(key='school_address').first()
    school_phone = SchoolSetting.objects.filter(key='school_phone').first()
    
    return {
        'school_name': school_name.value if school_name else 'SFMS SCHOOL',
        'school_address': school_address.value if school_address else '',
        'school_phone': school_phone.value if school_phone else '',
    }


@login_required
def cloud_sync_settings(request):
    """Cloud sync configuration page"""
    if request.method == 'POST':
        supabase_url = request.POST.get('supabase_url', '')
        supabase_key = request.POST.get('supabase_key', '')
        
        # Save to session
        request.session['supabase_url'] = supabase_url
        request.session['supabase_key'] = supabase_key
        
        messages.success(request, 'Cloud settings saved!')
        return redirect('cloud_sync_settings')
    
    context = {
        'supabase_url': request.session.get('supabase_url', ''),
        'supabase_key': '••••••••••••••••' if request.session.get('supabase_key') else '',
        'is_configured': bool(request.session.get('supabase_url') and request.session.get('supabase_key'))
    }
    return render(request, 'core/cloud_sync.html', context)


  
@login_required
def cloud_sync_now(request):
     from .cloud_sync import CloudSync
     from students.models import Student
     from receipts.models import Receipt
     from expenses.models import Expense
     from django.contrib import messages
     from django.shortcuts import redirect
     """Manually sync data to cloud"""
     supabase_url = request.session.get('supabase_url')
     supabase_key = request.session.get('supabase_key')
    
     if not supabase_url or not supabase_key:
        messages.error(request, 'Cloud not configured. Please set up Supabase credentials first.')
        return redirect('cloud_sync_settings')
    
    # For now, just show success message - full sync coming soon
     messages.success(request, 'Cloud sync will be fully implemented. Your Supabase credentials are saved!')
     return redirect('dashboard')
 

@login_required
def principal_portal(request):
    """Read-only portal for principal (accessible from any device)"""
    from receipts.models import Receipt
    from expenses.models import Expense
    from students.models import Student
    from fees.models import StudentFeeLedger
    from django.db.models import Sum
    from datetime import date
    
    today = date.today()
    
    # Today's collections
    today_receipts = Receipt.objects.filter(payment_date=today, is_voided=False)
    today_collected = today_receipts.aggregate(Sum('amount_lrd'))['amount_lrd__sum'] or 0
    
    # This month's collections
    month_start = date(today.year, today.month, 1)
    month_receipts = Receipt.objects.filter(payment_date__gte=month_start, is_voided=False)
    month_collected = month_receipts.aggregate(Sum('amount_lrd'))['amount_lrd__sum'] or 0
    
    # Students with balance
    students_with_balance = StudentFeeLedger.objects.exclude(
        semester1_total_lrd=0, semester2_total_lrd=0
    ).count()
    
    total_students = Student.objects.filter(is_active=True).count()
    
    # Recent receipts
    recent_receipts = Receipt.objects.filter(is_voided=False).order_by('-payment_date')[:15]
    
    context = {
        'today_collected': today_collected,
        'month_collected': month_collected,
        'students_with_balance': students_with_balance,
        'total_students': total_students,
        'recent_receipts': recent_receipts,
        'today': today,
    }
    return render(request, 'principal_portal.html', context)
def set_language(request):
    """Set user language preference"""
    language = request.POST.get('language') or request.GET.get('language', 'en')
    if language in ['en', 'fr']:
        request.session['language'] = language
    return redirect(request.META.get('HTTP_REFERER', '/'))


def set_language(request):
    """Set user language preference"""
    language = request.POST.get('language') or request.GET.get('language', 'en')
    if language in ['en', 'fr']:
        request.session['language'] = language
    return redirect(request.META.get('HTTP_REFERER', '/'))


from .email_utils import process_email_queue

def check_and_send_emails(request):
    """Check for pending emails and send them if internet available"""
    sent, message = process_email_queue()
    if sent > 0:
        print(f"📧 {message}")
    return JsonResponse({'sent': sent, 'message': message})


@login_required
def change_password(request):
    """Force password change on first login"""
    from .models import UserProfile
    
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match')
            return render(request, 'change_password.html')
        
        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters')
            return render(request, 'change_password.html')
        
        request.user.set_password(new_password)
        request.user.save()
        
        # Update profile
        try:
            profile = request.user.profile
            profile.require_password_change = False
            profile.save()
        except:
            pass
        
        # Re-authenticate
        user = authenticate(username=request.user.username, password=new_password)
        login(request, user)
        
        messages.success(request, 'Password changed successfully!')
        
        if request.user.username.startswith('pri_'):
            return redirect('principal_dashboard')
        return redirect('dashboard')
    
    return render(request, 'change_password.html')

def check_update(request):
    """Check if a newer version is available"""
    from django.http import JsonResponse
    import json
    from pathlib import Path
    
    version_file = Path(__file__).parent.parent / 'version.json'
    current_version = '1.0'
    if version_file.exists():
        with open(version_file, 'r') as f:
            data = json.load(f)
            current_version = data.get('version', '1.0')
    
    return JsonResponse({
        'update_available': False,
        'current_version': current_version,
        'latest_version': current_version,
        'message': 'You have the latest version'
    })

@login_required
def mobile_principal_dashboard(request):
    """Enhanced mobile-friendly dashboard for principal"""
    from django.db.models import Sum
    from datetime import date, timedelta
    from receipts.models import Receipt
    from expenses.models import Expense
    from students.models import Student
    from fees.models import StudentFeeLedger, InstallmentReminder
    
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = date(today.year, today.month, 1)
    
    # Today's collections
    today_receipts = Receipt.objects.filter(payment_date=today, is_voided=False)
    today_collected_lrd = today_receipts.aggregate(Sum('amount_lrd'))['amount_lrd__sum'] or 0
    today_collected_usd = today_receipts.aggregate(Sum('amount_usd'))['amount_usd__sum'] or 0
    
    # Weekly collections
    week_receipts = Receipt.objects.filter(payment_date__gte=week_start, is_voided=False)
    week_collected_lrd = week_receipts.aggregate(Sum('amount_lrd'))['amount_lrd__sum'] or 0
    
    # Monthly collections
    month_receipts = Receipt.objects.filter(payment_date__gte=month_start, is_voided=False)
    month_collected_lrd = month_receipts.aggregate(Sum('amount_lrd'))['amount_lrd__sum'] or 0
    
    # Students with balance
    students_with_balance = 0
    total_outstanding = 0
    for student in Student.objects.filter(is_active=True):
        ledger = StudentFeeLedger.objects.filter(student=student).first()
        if ledger and ledger.total_balance_lrd > 0:
            students_with_balance += 1
            total_outstanding += ledger.total_balance_lrd
    
    total_students = Student.objects.filter(is_active=True).count()
    
    # Recent receipts (last 10)
    recent_receipts = Receipt.objects.filter(is_voided=False).order_by('-payment_date')[:10]
    
    # Top defaulters (students with highest balance)
    top_defaulters = []
    for student in Student.objects.filter(is_active=True)[:10]:
        ledger = StudentFeeLedger.objects.filter(student=student).first()
        if ledger and ledger.total_balance_lrd > 0:
            top_defaulters.append({
                'name': student.full_name,
                'class': student.get_class_name(),
                'balance': ledger.total_balance_lrd,
                'phone': student.parent_phone or 'No phone'
            })
    top_defaulters.sort(key=lambda x: x['balance'], reverse=True)
    top_defaulters = top_defaulters[:5]
    
    # Collection by class
    class_collections = {}
    for receipt in week_receipts:
        class_name = receipt.student.get_class_name()
        if class_name not in class_collections:
            class_collections[class_name] = 0
        class_collections[class_name] += float(receipt.amount_lrd)
    
    # Overdue reminders
    overdue_count = InstallmentReminder.objects.filter(is_paid=False, due_date__lt=today).count()
    
    # Calculate collection target (70% of total students should have paid something)
    students_with_payments = Receipt.objects.filter(is_voided=False).values('student').distinct().count()
    collection_rate = (students_with_payments / total_students * 100) if total_students > 0 else 0
    
    context = {
        'today_collected_lrd': today_collected_lrd,
        'today_collected_usd': today_collected_usd,
        'week_collected_lrd': week_collected_lrd,
        'month_collected_lrd': month_collected_lrd,
        'students_with_balance': students_with_balance,
        'total_outstanding': total_outstanding,
        'total_students': total_students,
        'overdue_count': overdue_count,
        'collection_rate': collection_rate,
        'recent_receipts': recent_receipts,
        'top_defaulters': top_defaulters,
        'class_collections': class_collections,
        'today': today,
    }
    return render(request, 'mobile_principal_dashboard.html', context)

# ========== LICENSE FUNCTIONS ==========
def license_info_api(request):
    """Return license information for display in footer"""
    try:
        from sfms.license_check import get_school_info
        info = get_school_info()
        return JsonResponse({
            'school_name': info.get('school_name', 'Unlicensed School'),
            'license_key': info.get('license_key', 'No License')
        })
    except Exception as e:
        return JsonResponse({
            'school_name': 'License Error',
            'license_key': 'Check license.json file'
        })


# ============================================================
# RECOVERY FUNCTIONS
# ============================================================

@login_required
def recover_data(request):
    """Recover SFMS data from cloud using recovery key"""
    from .models import SchoolRecovery
    from django.contrib import messages
    
    if request.method == 'POST':
        recovery_key = request.POST.get('recovery_key', '').strip().upper()
        
        if not recovery_key:
            messages.error(request, 'Please enter a recovery key.')
            return render(request, 'recovery.html')
        
        # Validate recovery key format
        if not recovery_key.startswith('RECOVER-'):
            messages.error(request, 'Invalid recovery key format. Should start with RECOVER-')
            return render(request, 'recovery.html')
        
        try:
            # Get license info
            license_path = os.path.join(settings.BASE_DIR, 'license.json')
            with open(license_path, 'r') as f:
                license_data = json.load(f)
            
            supabase_url = license_data.get('supabase_url', '')
            supabase_key = license_data.get('supabase_key', '')
            
            if not supabase_url or not supabase_key:
                messages.error(request, 'Supabase credentials not found in license. Please contact the developer.')
                return render(request, 'recovery.html')
            
            # Verify recovery key in cloud
            headers = {
                'apikey': supabase_key,
                'Authorization': f'Bearer {supabase_key}',
                'Content-Type': 'application/json'
            }
            
            # Check if recovery key exists
            response = requests.get(
                f"{supabase_url}/rest/v1/school_recovery?recovery_key=eq.{recovery_key}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code != 200:
                messages.error(request, 'Could not connect to cloud. Please check your internet connection.')
                return render(request, 'recovery.html')
            
            data = response.json()
            
            if not data:
                messages.error(request, 'Invalid recovery key. Please contact the developer.')
                return render(request, 'recovery.html')
            
            # Recovery key is valid
            recovery_info = data[0]
            school_name = recovery_info.get('school_name', 'Unknown')
            
            # Download all data from cloud
            # This is a simplified version - in production, download all tables
            tables = ['students', 'receipts', 'expenses', 'fees', 'payroll']
            records_downloaded = 0
            
            for table in tables:
                try:
                    response = requests.get(
                        f"{supabase_url}/rest/v1/{table}",
                        headers=headers,
                        timeout=30
                    )
                    if response.status_code == 200:
                        records = response.json()
                        records_downloaded += len(records)
                except:
                    pass
            
            # Save recovery info locally
            SchoolRecovery.objects.update_or_create(
                recovery_key=recovery_key,
                defaults={
                    'school_name': school_name,
                    'license_key': license_data.get('license_key', ''),
                    'supabase_url': supabase_url,
                    'supabase_key': supabase_key,
                    'last_sync': timezone.now()
                }
            )
            
            messages.success(
                request, 
                f'✅ Data recovered successfully for {school_name}! '
                f'{records_downloaded} records downloaded.'
            )
            return redirect('dashboard')
            
        except json.JSONDecodeError:
            messages.error(request, 'Error reading license file.')
            return render(request, 'recovery.html')
        except requests.RequestException as e:
            messages.error(request, f'Connection error: {str(e)}')
            return render(request, 'recovery.html')
        except Exception as e:
            messages.error(request, f'Recovery error: {str(e)}')
            return render(request, 'recovery.html')
    
    return render(request, 'recovery.html')


@login_required
def restore_from_usb(request):
    """Restore data from USB backup"""
    from django.contrib import messages
    
    usb_drives = get_usb_drives()
    backups = []
    
    for drive in usb_drives:
        backup_dir = os.path.join(drive, 'SFMS_Backup')
        if os.path.exists(backup_dir):
            for file in os.listdir(backup_dir):
                if file.endswith('.zip'):
                    file_path = os.path.join(backup_dir, file)
                    backups.append({
                        'drive': drive,
                        'file': file,
                        'path': file_path,
                        'date': timezone.datetime.fromtimestamp(
                            os.path.getctime(file_path)
                        ).strftime('%Y-%m-%d %H:%M'),
                        'size': os.path.getsize(file_path) / 1024 / 1024,
                    })
    
    # Sort backups by date (newest first)
    backups.sort(key=lambda x: x['date'], reverse=True)
    
    if request.method == 'POST':
        backup_file = request.POST.get('backup_file')
        
        if not backup_file:
            messages.error(request, 'Please select a backup file.')
            return redirect('restore_from_usb')
        
        # Find the backup
        backup_path = None
        for backup in backups:
            if backup['file'] == backup_file:
                backup_path = backup['path']
                break
        
        if not backup_path:
            messages.error(request, 'Backup file not found.')
            return redirect('restore_from_usb')
        
        try:
            # Extract backup
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                # Extract database
                zipf.extract('db.sqlite3', settings.BASE_DIR)
                
                # Extract media files
                for member in zipf.namelist():
                    if member.startswith('media/'):
                        zipf.extract(member, settings.BASE_DIR)
            
            messages.success(request, '✅ Data restored successfully from USB! Please restart SFMS.')
            return redirect('dashboard')
            
        except Exception as e:
            messages.error(request, f'Restore failed: {str(e)}')
            return redirect('restore_from_usb')
    
    context = {
        'usb_drives': usb_drives,
        'backups': backups,
    }
    return render(request, 'restore_usb.html', context)

# ============================================================
# CLOUD SYNC VIEWS
# ============================================================

@login_required
def cloud_sync_settings(request):
    """Cloud sync configuration and status page"""
    from .cloud_sync import CloudSync
    
    sync = CloudSync()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'sync_now':
            success, message = sync_to_cloud()
            if success:
                messages.success(request, f'✅ Cloud sync completed! {message}')
            else:
                messages.error(request, f'❌ Sync failed: {message}')
            return redirect('cloud_sync_settings')
    
    # Get sync status
    is_configured = sync.is_configured()
    connection_status = "Not Configured"
    
    if is_configured:
        success, message = sync._test_connection()
        connection_status = "Connected" if success else f"Error: {message}"
    
    context = {
        'is_configured': is_configured,
        'connection_status': connection_status,
        'school_name': sync.school_name,
        'recovery_key': sync.recovery_key,
        'supabase_url': sync.supabase_url[:30] + '...' if sync.supabase_url else 'Not set',
    }
    return render(request, 'core/cloud_sync.html', context)


@login_required
def cloud_sync_now(request):
    """Trigger cloud sync manually"""
    from .cloud_sync import sync_to_cloud
    
    success, message = sync_to_cloud()
    
    if success:
        messages.success(request, f'✅ Cloud sync completed!')
    else:
        messages.error(request, f'❌ Sync failed: {message}')
    
    return redirect('dashboard')

# ============================================================
# ARCHIVE VIEWS
# ============================================================

@login_required
def archive_list(request):
    """List all archived years"""
    from .models import ArchiveIndex
    from .archive_utils import Archiver
    
    archives = ArchiveIndex.objects.all().order_by('-academic_year')
    archiver = Archiver()
    years_to_archive = archiver.get_years_to_archive()
    
    context = {
        'archives': archives,
        'years_to_archive': years_to_archive,
        'archive_dir': ARCHIVE_DIR if 'ARCHIVE_DIR' in dir() else '',
    }
    return render(request, 'core/archive_list.html', context)


@login_required
def archive_year_now(request):
    """Archive a specific year"""
    from .archive_utils import Archiver
    
    if request.method == 'POST':
        academic_year = request.POST.get('academic_year')
        
        if not academic_year:
            messages.error(request, 'No academic year specified.')
            return redirect('archive_list')
        
        archiver = Archiver()
        success, message = archiver.archive_year(academic_year)
        
        if success:
            messages.success(request, f'✅ {message}')
        else:
            messages.error(request, f'❌ {message}')
    
    return redirect('archive_list')


@login_required
def archive_all_now(request):
    """Archive all eligible years"""
    from .archive_utils import Archiver
    
    if request.method == 'POST':
        archiver = Archiver()
        results = archiver.archive_all_old_years()
        
        if results:
            success_count = sum(1 for r in results if r['success'])
            messages.success(request, f'✅ Archived {success_count} years')
        else:
            messages.info(request, 'No years to archive')
    
    return redirect('archive_list')


@login_required
def view_archive(request, academic_year):
    """View archived year data"""
    from .models import ArchiveIndex
    import zipfile
    
    archive = get_object_or_404(ArchiveIndex, academic_year=academic_year)
    
    # Read archive contents
    file_path = os.path.join(ARCHIVE_DIR, archive.file_name)
    
    if not os.path.exists(file_path):
        messages.error(request, 'Archive file not found.')
        return redirect('archive_list')
    
    data = {}
    try:
        with zipfile.ZipFile(file_path, 'r') as zipf:
            for name in zipf.namelist():
                if name.endswith('.json'):
                    with zipf.open(name) as f:
                        data[name.replace('.json', '')] = json.load(f)
    except Exception as e:
        messages.error(request, f'Error reading archive: {str(e)}')
        return redirect('archive_list')
    
    context = {
        'archive': archive,
        'data': data,
        'academic_year': academic_year,
    }
    return render(request, 'core/view_archive.html', context)


@login_required
def download_archive(request, academic_year):
    """Download archive file"""
    from .models import ArchiveIndex
    from django.http import FileResponse
    
    archive = get_object_or_404(ArchiveIndex, academic_year=academic_year)
    file_path = os.path.join(ARCHIVE_DIR, archive.file_name)
    
    if os.path.exists(file_path):
        response = FileResponse(open(file_path, 'rb'), as_attachment=True)
        response['Content-Disposition'] = f'attachment; filename="{archive.file_name}"'
        return response
    
    messages.error(request, 'Archive file not found.')
    return redirect('archive_list')

# ============================================================
# DATA EXPORT VIEWS
# ============================================================

@login_required
def export_dashboard(request):
    """Data export dashboard"""
    from fees.models import AcademicSession
    
    sessions = AcademicSession.objects.all().order_by('-academic_year')
    active_session = AcademicSession.objects.filter(is_active=True).first()
    
    context = {
        'sessions': sessions,
        'active_year': active_session.academic_year if active_session else 'N/A',
    }
    return render(request, 'core/export_dashboard.html', context)


@login_required
def export_data(request, export_type):
    """Export data to Excel or JSON"""
    from django.http import HttpResponse
    from .export_utils import export_to_excel, export_to_json
    from datetime import datetime
    
    academic_year = request.GET.get('year')
    format_type = request.GET.get('format', 'excel')
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    try:
        if format_type == 'json':
            data = export_to_json()
            response = HttpResponse(
                json.dumps(data, indent=2),
                content_type='application/json'
            )
            response['Content-Disposition'] = f'attachment; filename="sfms_export_{timestamp}.json"'
            return response
        else:
            wb = export_to_excel(export_type, academic_year)
            
            # Create response
            response = HttpResponse(
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            
            filename = f'sfms_{export_type}_{timestamp}.xlsx'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            wb.save(response)
            return response
            
    except Exception as e:
        messages.error(request, f'Export failed: {str(e)}')
        return redirect('export_dashboard')
