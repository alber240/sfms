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
    from datetime import date
    from django.db.models import Sum
    
    today = date.today()
    
    # Get today's exchange rate or most recent
    exchange_rate_obj = ExchangeRate.objects.filter(rate_date=today).first()
    if not exchange_rate_obj:
        exchange_rate_obj = ExchangeRate.objects.first()
    
    exchange_rate = exchange_rate_obj.lrd_to_usd if exchange_rate_obj else 200
    
    # Today's collections
    today_receipts = Receipt.objects.filter(payment_date=today, is_voided=False)
    total_collected_lrd = today_receipts.aggregate(Sum('amount_lrd'))['amount_lrd__sum'] or 0
    total_collected_usd = today_receipts.aggregate(Sum('amount_usd'))['amount_usd__sum'] or 0
    
    # Today's expenses
    today_expenses = Expense.objects.filter(expense_date=today)
    total_expenses_lrd = today_expenses.aggregate(Sum('amount_lrd'))['amount_lrd__sum'] or 0
    total_expenses_usd = today_expenses.aggregate(Sum('amount_usd'))['amount_usd__sum'] or 0
    
    # Calculate net separately
    net_lrd = total_collected_lrd - total_expenses_lrd
    net_usd = total_collected_usd - total_expenses_usd
    net_combined = net_lrd + (net_usd * exchange_rate)
    
    recent_receipts = Receipt.objects.filter(is_voided=False).order_by('-payment_date', '-id')[:10]
    
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
