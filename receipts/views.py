from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from django.db.models import Q
from datetime import date
from decimal import Decimal

from students.models import Student
from fees.models import StudentFeeLedger
from .models import Receipt, ReceiptSequence, BatchPaymentSession
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from django.db.models import Q
from datetime import date
from students.models import Student
from fees.models import StudentFeeLedger
from .models import Receipt

@login_required
@login_required

@login_required

@login_required
def payment_entry(request, student_id=None):
    from fees.models import StudentFeeLedger
    from fees.views import get_active_academic_year
    
    student = None
    balance_lrd = 0
    balance_usd = 0
    total_due_lrd = 0
    total_due_usd = 0
    
    if student_id:
        student = get_object_or_404(Student, id=student_id)
        academic_year = get_active_academic_year()
        
        # Get current balance from fee ledger
        ledger = StudentFeeLedger.objects.filter(student=student, academic_year=academic_year).first()
        if ledger:
            # Calculate remaining balance (total - paid)
            balance_lrd = (ledger.semester1_total_lrd + ledger.semester2_total_lrd) - (ledger.semester1_paid_lrd + ledger.semester2_paid_lrd)
            balance_usd = (ledger.semester1_total_usd + ledger.semester2_total_usd) - (ledger.semester1_paid_usd + ledger.semester2_paid_usd)
            total_due_lrd = ledger.semester1_total_lrd + ledger.semester2_total_lrd
            total_due_usd = ledger.semester1_total_usd + ledger.semester2_total_usd
    
    # ... rest of the function ...
    
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        student = get_object_or_404(Student, id=student_id)
        payment_period = request.POST.get('payment_period', 'FIRST')
        
        amount_lrd = Decimal(request.POST.get('amount_lrd', '0') or '0')
        amount_usd = Decimal(request.POST.get('amount_usd', '0') or '0')
        
        if amount_lrd == 0 and amount_usd == 0:
            messages.error(request, 'Please enter an amount in LRD or USD')
            return redirect('payment_entry', student_id=student.id)
        
        # Create receipt
        receipt = Receipt.objects.create(
            student=student,
            payment_date=date.today(),
            amount_lrd=amount_lrd,
            amount_usd=amount_usd,
            payment_method=request.POST.get('payment_method', 'CASH'),
            mobile_transaction_id=request.POST.get('mobile_transaction_id', ''),
        )
        
        # Update student fee ledger based on payment period
        ledger = StudentFeeLedger.objects.filter(student=student).first()
        
        if ledger:
            if payment_period == 'FIRST':
                ledger.semester1_paid_lrd += amount_lrd
                ledger.semester1_paid_usd += amount_usd
            elif payment_period == 'SECOND':
                ledger.semester2_paid_lrd += amount_lrd
                ledger.semester2_paid_usd += amount_usd
            else:  # YEARLY - split between semesters based on actual fee structure
                total_sem1 = float(ledger.semester1_total_lrd)
                total_sem2 = float(ledger.semester2_total_lrd)
                total = total_sem1 + total_sem2
                if total > 0:
                    ratio = Decimal(str(total_sem1 / total))
                else:
                    ratio = Decimal('0.5')
                
                ledger.semester1_paid_lrd += amount_lrd * ratio
                ledger.semester2_paid_lrd += amount_lrd * (Decimal('1') - ratio)
                ledger.semester1_paid_usd += amount_usd * ratio
                ledger.semester2_paid_usd += amount_usd * (Decimal('1') - ratio)
            
            ledger.last_payment_date = date.today()
            ledger.save()
        
        messages.success(request, f'Receipt #{receipt.receipt_number} created successfully!')
        return redirect('receipt_print', receipt_id=receipt.id)
    
    context = {
        'student': student,
        'balance_lrd': float(balance_lrd),
        'balance_usd': float(balance_usd),
        'total_due_lrd': float(total_due_lrd),
        'total_due_usd': float(total_due_usd),
    }
    return render(request, 'receipts/payment.html', context)

@login_required

@login_required
def receipt_print(request, receipt_id):
    from core.models import SchoolSetting
    
    receipt = get_object_or_404(Receipt, id=receipt_id)
    
    # Get updated balance after this payment
    current_ledger = StudentFeeLedger.objects.filter(student=receipt.student).first()
    
    if current_ledger:
        remaining_balance_lrd = (current_ledger.semester1_total_lrd + current_ledger.semester2_total_lrd) - (current_ledger.semester1_paid_lrd + current_ledger.semester2_paid_lrd) - current_ledger.discount_applied_lrd
        remaining_balance_usd = (current_ledger.semester1_total_usd + current_ledger.semester2_total_usd) - (current_ledger.semester1_paid_usd + current_ledger.semester2_paid_usd) - current_ledger.discount_applied_usd
    else:
        remaining_balance_lrd = 0
        remaining_balance_usd = 0
    
    # Get school settings including accountant name
    school_name = SchoolSetting.objects.filter(key='school_name').first()
    school_accountant_name = SchoolSetting.objects.filter(key='accountant_name').first()
    
    context = {
        'receipt': receipt,
        'remaining_balance_lrd': remaining_balance_lrd,
        'remaining_balance_usd': remaining_balance_usd,
        'school_name': school_name.value if school_name else 'SFMS SCHOOL',
        'school_accountant_name': school_accountant_name.value if school_accountant_name else '',
    }
    return render(request, 'receipts/print.html', context)

@login_required

@login_required
def quick_payment(request):
    students = []
    search = ''
    if request.method == 'POST':
        search = request.POST.get('search', '')
        if search:
            students = Student.objects.filter(
                models.Q(first_name__icontains=search) |
                models.Q(last_name__icontains=search) |
                models.Q(admission_number__icontains=search) |
                models.Q(parent_phone__icontains=search)
            )[:10]
            
            # Add balance info to each student using new semester structure
            for student in students:
                ledger = StudentFeeLedger.objects.filter(student=student).first()
                if ledger:
                    student.balance_lrd = (ledger.semester1_total_lrd + ledger.semester2_total_lrd) - (ledger.semester1_paid_lrd + ledger.semester2_paid_lrd) - ledger.discount_applied_lrd
                    student.balance_usd = (ledger.semester1_total_usd + ledger.semester2_total_usd) - (ledger.semester1_paid_usd + ledger.semester2_paid_usd) - ledger.discount_applied_usd
                else:
                    student.balance_lrd = 0
                    student.balance_usd = 0
    
    return render(request, 'receipts/quick_payment.html', {'students': students, 'search': search})


@login_required

@login_required
def batch_payment(request):
    """Record multiple students' payments at once"""
    from decimal import Decimal
    
    students = []
    search = ''
    selected_students = []
    payment_period = request.POST.get('payment_period', 'FIRST')
    academic_year = request.POST.get('academic_year', '2024-2025')
    
    # Handle search
    if request.method == 'POST' and 'search_btn' in request.POST:
        search = request.POST.get('search', '')
        if search:
            students = Student.objects.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(admission_number__icontains=search) |
                Q(parent_phone__icontains=search),
                is_active=True
            )[:20]
            
            # Add balance info to each student
            for student in students:
                ledger = StudentFeeLedger.objects.filter(student=student).first()
                if ledger:
                    if payment_period == 'FIRST':
                        student.balance = float(ledger.semester1_total_lrd - ledger.semester1_paid_lrd)
                    elif payment_period == 'SECOND':
                        student.balance = float(ledger.semester2_total_lrd - ledger.semester2_paid_lrd)
                    else:
                        student.balance = float((ledger.semester1_total_lrd + ledger.semester2_total_lrd) - (ledger.semester1_paid_lrd + ledger.semester2_paid_lrd))
                else:
                    student.balance = 0
    
    # Handle adding students to batch
    if request.method == 'POST' and 'add_to_batch' in request.POST:
        selected_ids = request.POST.getlist('selected_students')
        if 'batch_students' not in request.session:
            request.session['batch_students'] = []
        
        for sid in selected_ids:
            if sid not in request.session['batch_students']:
                request.session['batch_students'].append(sid)
        request.session.modified = True
        messages.success(request, f'Added {len(selected_ids)} students to batch')
        return redirect('batch_payment')
    
    # Handle removing students from batch
    if request.method == 'POST' and 'remove_from_batch' in request.POST:
        remove_id = request.POST.get('remove_from_batch')
        if remove_id and remove_id in request.session.get('batch_students', []):
            request.session['batch_students'].remove(remove_id)
            request.session.modified = True
            messages.success(request, 'Student removed from batch')
        return redirect('batch_payment')
    
    # Handle processing batch payments
    if request.method == 'POST' and 'process_batch' in request.POST:
        batch_students = request.session.get('batch_students', [])
        payment_method = request.POST.get('payment_method', 'CASH')
        payment_period = request.POST.get('payment_period', 'FIRST')
        academic_year = request.POST.get('academic_year', '2024-2025')
        
        receipts_created = 0
        total_lrd = Decimal('0')
        total_usd = Decimal('0')
        
        for student_id in batch_students:
            student = get_object_or_404(Student, id=student_id)
            amount_lrd = Decimal(request.POST.get(f'amount_lrd_{student_id}', '0') or '0')
            amount_usd = Decimal(request.POST.get(f'amount_usd_{student_id}', '0') or '0')
            
            if amount_lrd == 0 and amount_usd == 0:
                continue
            
            # Create receipt
            receipt = Receipt.objects.create(
                student=student,
                payment_date=date.today(),
                amount_lrd=amount_lrd,
                amount_usd=amount_usd,
                payment_method=payment_method,
            )
            
            # Update ledger
            ledger = StudentFeeLedger.objects.filter(student=student).first()
            if ledger:
                if payment_period == 'FIRST':
                    ledger.semester1_paid_lrd += amount_lrd
                    ledger.semester1_paid_usd += amount_usd
                elif payment_period == 'SECOND':
                    ledger.semester2_paid_lrd += amount_lrd
                    ledger.semester2_paid_usd += amount_usd
                else:  # YEARLY
                    total_sem1 = float(ledger.semester1_total_lrd)
                    total_sem2 = float(ledger.semester2_total_lrd)
                    total = total_sem1 + total_sem2
                    if total > 0:
                        ratio = Decimal(str(total_sem1 / total))
                    else:
                        ratio = Decimal('0.5')
                    
                    ledger.semester1_paid_lrd += amount_lrd * ratio
                    ledger.semester2_paid_lrd += amount_lrd * (Decimal('1') - ratio)
                    ledger.semester1_paid_usd += amount_usd * ratio
                    ledger.semester2_paid_usd += amount_usd * (Decimal('1') - ratio)
                
                ledger.last_payment_date = date.today()
                ledger.save()
            
            receipts_created += 1
            total_lrd += amount_lrd
            total_usd += amount_usd
        
        # Clear batch session
        request.session['batch_students'] = []
        request.session.modified = True
        
        messages.success(request, f'✅ Processed {receipts_created} receipts! Total: {total_lrd} LRD, {total_usd} USD')
        return redirect('dashboard')
    
    # Get current batch students with details
    batch_students = []
    batch_student_ids = request.session.get('batch_students', [])
    if batch_student_ids:
        batch_students = Student.objects.filter(id__in=batch_student_ids, is_active=True)
        for student in batch_students:
            ledger = StudentFeeLedger.objects.filter(student=student).first()
            if ledger:
                if payment_period == 'FIRST':
                    student.due = float(ledger.semester1_total_lrd - ledger.semester1_paid_lrd)
                elif payment_period == 'SECOND':
                    student.due = float(ledger.semester2_total_lrd - ledger.semester2_paid_lrd)
                else:
                    student.due = float((ledger.semester1_total_lrd + ledger.semester2_total_lrd) - (ledger.semester1_paid_lrd + ledger.semester2_paid_lrd))
            else:
                student.due = 0
    
    context = {
        'students': students,
        'search': search,
        'batch_students': batch_students,
        'payment_period': payment_period,
        'academic_year': academic_year,
        'available_years': ['2024-2025', '2025-2026', '2026-2027'],
    }
    return render(request, 'receipts/batch_payment.html', context)








