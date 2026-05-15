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

# Safe imports for fees models
try:
    from fees.models import StudentFeeLedger, InstallmentReminder
except ImportError:
    StudentFeeLedger = None
    InstallmentReminder = None

def login_view(request):
    if request.user.is_authenticated:
        if request.user.username == 'principal':
            return redirect('principal_dashboard')
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            if username == 'principal':
                return redirect('principal_dashboard')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password')
    
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
@login_required
def dashboard_view(request):
    from .models import ExchangeRate
    from datetime import date
    
    today = date.today()
    
    # Get today's exchange rate or most recent
    exchange_rate_obj = ExchangeRate.objects.filter(rate_date=today).first()
    if not exchange_rate_obj:
        exchange_rate_obj = ExchangeRate.objects.first()
    
    exchange_rate = exchange_rate_obj.lrd_to_usd if exchange_rate_obj else 200
    
    today_receipts = Receipt.objects.filter(payment_date=today, is_voided=False)
    total_collected_lrd = today_receipts.aggregate(Sum('amount_lrd'))['amount_lrd__sum'] or 0
    total_collected_usd = today_receipts.aggregate(Sum('amount_usd'))['amount_usd__sum'] or 0
    
    today_expenses = Expense.objects.filter(expense_date=today)
    total_expenses_lrd = today_expenses.aggregate(Sum('amount_lrd'))['amount_lrd__sum'] or 0
    total_expenses_usd = today_expenses.aggregate(Sum('amount_usd'))['amount_usd__sum'] or 0
    
    net_combined = (total_collected_lrd - total_expenses_lrd) + ((total_collected_usd - total_expenses_usd) * exchange_rate)
    
    recent_receipts = Receipt.objects.filter(is_voided=False).order_by('-payment_date', '-id')[:10]
    
    context = {
        'total_collected_lrd': total_collected_lrd,
        'total_collected_usd': total_collected_usd,
        'total_expenses_lrd': total_expenses_lrd,
        'total_expenses_usd': total_expenses_usd,
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
    """Check if 4 PM reminder should be shown"""
    from .models import DailyReminder
    from datetime import datetime, time
    
    now = datetime.now()
    today = now.date()
    reminder_time = time(0, 0)  # 4 PM
    
    # Check if it's after 4 PM and reminder not dismissed today
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

