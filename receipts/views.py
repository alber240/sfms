from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import models
from django.db.models import Q
from datetime import date
from decimal import Decimal
from fees.models import FeeCategory

from fees.views import get_active_academic_year
from students.models import Student
from fees.models import StudentFeeLedger
from .models import Receipt, ReceiptSequence
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
    from decimal import Decimal
    from fees.models import FeeCategory, FeeStructure
    from .models import PaymentAllocation
    
    student = None
    fee_categories = []
    
    if student_id:
        student = get_object_or_404(Student, id=student_id)
        academic_year = get_active_academic_year()
        
        # Get fee structure for this student
        fee_structures = FeeStructure.objects.filter(
            class_assigned=student.class_assigned,
            academic_year=academic_year,
            student_type=student.student_type,
            is_active=True
        ).select_related('category')
        
        for fs in fee_structures:
            due_lrd = fs.semester1_amount_lrd + fs.semester2_amount_lrd
            due_usd = fs.semester1_amount_usd + fs.semester2_amount_usd
            
            # Calculate paid amount for this category
            paid_lrd = Decimal('0')
            paid_usd = Decimal('0')
            receipts = Receipt.objects.filter(student=student, is_voided=False, is_legacy=False)
            for receipt in receipts:
                allocations = receipt.allocations.filter(fee_category=fs.category)
                paid_lrd += sum(a.amount_lrd for a in allocations)
                paid_usd += sum(a.amount_usd for a in allocations)
            
            balance_lrd = due_lrd - paid_lrd
            balance_usd = due_usd - paid_usd
            
            fee_categories.append({
                'id': fs.category.id,
                'name': fs.category.name,
                'code': fs.category.code,
                'due_lrd': float(due_lrd),
                'due_usd': float(due_usd),
                'paid_lrd': float(paid_lrd),
                'paid_usd': float(paid_usd),
                'balance_lrd': float(max(balance_lrd, 0)),
                'balance_usd': float(max(balance_usd, 0)),
            })
    
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        student = get_object_or_404(Student, id=student_id)
        payment_period = request.POST.get('payment_period', 'FIRST')
        # FIX: Get the fee_category_id as integer
        fee_category_id = request.POST.get('fee_category')
        amount_lrd = Decimal(request.POST.get('amount_lrd', '0') or '0')
        amount_usd = Decimal(request.POST.get('amount_usd', '0') or '0')
        
        # Validate fee_category_id is a number
        try:
            fee_category_id = int(fee_category_id)
        except (ValueError, TypeError):
            messages.error(request, 'Please select a valid fee category')
            return redirect('payment_entry', student_id=student.id)
        
        # Get the selected fee category
        selected_category = get_object_or_404(FeeCategory, id=fee_category_id)
        academic_year = get_active_academic_year()
        
        fee_structure = FeeStructure.objects.filter(
            class_assigned=student.class_assigned,
            academic_year=academic_year,
            student_type=student.student_type,
            category=selected_category,
            is_active=True
        ).first()
        
        if fee_structure:
            if payment_period == 'FIRST':
                due_for_category = fee_structure.semester1_amount_lrd
                due_for_category_usd = fee_structure.semester1_amount_usd
            elif payment_period == 'SECOND':
                due_for_category = fee_structure.semester2_amount_lrd
                due_for_category_usd = fee_structure.semester2_amount_usd
            else:  # YEARLY
                due_for_category = fee_structure.semester1_amount_lrd + fee_structure.semester2_amount_lrd
                due_for_category_usd = fee_structure.semester1_amount_usd + fee_structure.semester2_amount_usd
            
            # Calculate already paid for this category
            already_paid = Decimal('0')
            receipts = Receipt.objects.filter(student=student, is_voided=False, is_legacy=False)
            for receipt in receipts:
                allocations = receipt.allocations.filter(fee_category=selected_category)
                already_paid += sum(a.amount_lrd for a in allocations)
            
            remaining_due = due_for_category - already_paid
            
            # Check for overpayment
            if amount_lrd > remaining_due and remaining_due > 0:
                overpayment = amount_lrd - remaining_due
                messages.warning(request, f'⚠️ Overpayment Warning: {selected_category.name} fee is {remaining_due} LRD. You entered {amount_lrd} LRD (Overpayment of {overpayment} LRD).')
                return render(request, 'receipts/overpayment_warning.html', {
                    'student': student,
                    'category': selected_category,
                    'due_amount': remaining_due,
                    'entered_amount': amount_lrd,
                    'overpayment': overpayment,
                    'payment_period': payment_period,
                })
        
        # Create receipt
        receipt = Receipt.objects.create(
            student=student,
            payment_date=date.today(),
            amount_lrd=amount_lrd,
            amount_usd=amount_usd,
            payment_method=request.POST.get('payment_method', 'CASH'),
            mobile_transaction_id=request.POST.get('mobile_transaction_id', ''),
            is_legacy=False,
            payment_period=payment_period,
        )
        
        # Create allocation
        PaymentAllocation.objects.create(
            receipt=receipt,
            fee_category=selected_category,
            amount_lrd=amount_lrd,
            amount_usd=amount_usd,
        )
        
        messages.success(request, f'Receipt #{receipt.receipt_number} created successfully!')
        return redirect('receipt_print', receipt_id=receipt.id)
    
    total_due_lrd = sum(f['due_lrd'] for f in fee_categories)
    total_due_usd = sum(f['due_usd'] for f in fee_categories)
    total_paid_lrd = sum(f['paid_lrd'] for f in fee_categories)
    total_paid_usd = sum(f['paid_usd'] for f in fee_categories)
    total_balance_lrd = total_due_lrd - total_paid_lrd
    total_balance_usd = total_due_usd - total_paid_usd
    
    context = {
        'student': student,
        'fee_categories': fee_categories,
        'total_due_lrd': total_due_lrd,
        'total_due_usd': total_due_usd,
        'total_paid_lrd': total_paid_lrd,
        'total_paid_usd': total_paid_usd,
        'total_balance_lrd': total_balance_lrd,
        'total_balance_usd': total_balance_usd,
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
def batch_payment(request):
    """Record multiple students' payments at once"""
    from decimal import Decimal
    from .models import Receipt, ReceiptSequence, PaymentAllocation
    from fees.models import FeeCategory, StudentFeeLedger
    
    students = []
    search = ''
    payment_period = request.POST.get('payment_period', 'FIRST')
    academic_year = request.POST.get('academic_year', '2024-2025')
    fee_categories = FeeCategory.objects.filter(is_active=True)
    
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
                        student.balance = float((ledger.semester1_total_lrd + ledger.semester2_total_lrd) - 
                                               (ledger.semester1_paid_lrd + ledger.semester2_paid_lrd))
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
    
    # ============================================================
    # Handle processing batch payments (FIXED)
    # ============================================================
    if request.method == 'POST' and 'process_batch' in request.POST:
        batch_students = request.session.get('batch_students', [])
        payment_method = request.POST.get('payment_method', 'CASH')
        payment_period = request.POST.get('payment_period', 'FIRST')
        academic_year = request.POST.get('academic_year', '2024-2025')
        fee_category_id = request.POST.get('fee_category')
        
        # Validate fee category
        if not fee_category_id:
            messages.error(request, 'Please select a fee category.')
            return redirect('batch_payment')
        
        try:
            fee_category = FeeCategory.objects.get(id=int(fee_category_id))
        except (ValueError, FeeCategory.DoesNotExist):
            messages.error(request, 'Invalid fee category selected.')
            return redirect('batch_payment')
        
        receipts_created = 0
        total_lrd = Decimal('0')
        total_usd = Decimal('0')
        
        for student_id in batch_students:
            student = get_object_or_404(Student, id=student_id)
            amount_lrd = Decimal(request.POST.get(f'amount_lrd_{student_id}', '0') or '0')
            amount_usd = Decimal(request.POST.get(f'amount_usd_{student_id}', '0') or '0')
            
            if amount_lrd == 0 and amount_usd == 0:
                continue
            
            # Get next receipt number using the model's method
            receipt_number = ReceiptSequence.get_next_number()
            
            # Create receipt
            receipt = Receipt.objects.create(
                student=student,
                receipt_number=receipt_number,
                payment_date=date.today(),
                amount_lrd=amount_lrd,
                amount_usd=amount_usd,
                payment_method=payment_method,
                payment_period=payment_period,
                is_legacy=False,
                is_voided=False
            )
            
            # ============================================================
            # FIX: Create PaymentAllocation record (THIS WAS MISSING!)
            # ============================================================
            PaymentAllocation.objects.create(
                receipt=receipt,
                fee_category=fee_category,
                amount_lrd=amount_lrd,
                amount_usd=amount_usd
            )
            
            # Update ledger
            ledger = StudentFeeLedger.objects.filter(student=student, academic_year=academic_year).first()
            
            if not ledger:
                # If no ledger exists, try without academic_year filter
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
                    student.due = float((ledger.semester1_total_lrd + ledger.semester2_total_lrd) - 
                                       (ledger.semester1_paid_lrd + ledger.semester2_paid_lrd))
            else:
                student.due = 0
    
    context = {
        'students': students,
        'search': search,
        'batch_students': batch_students,
        'payment_period': payment_period,
        'academic_year': academic_year,
        'available_years': ['2024-2025', '2025-2026', '2026-2027'],
        'fee_categories': fee_categories,
    }
    return render(request, 'receipts/batch_payment.html', context)

@login_required
def handle_overpayment(request):
    """Handle overpayment by applying extra to next fee or creating credit"""
    from decimal import Decimal
    from fees.models import FeeCategory, FeeStructure
    from .models import Receipt, PaymentAllocation
    
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        category_id = request.POST.get('category_id')
        amount = Decimal(request.POST.get('amount', '0'))
        payment_period = request.POST.get('payment_period', 'FIRST')
        action = request.POST.get('overpayment_action', 'next_fee')
        
        student = get_object_or_404(Student, id=student_id)
        category = get_object_or_404(FeeCategory, id=category_id)
        academic_year = get_active_academic_year()
        
        # Get fee structure for this category
        fee_structure = FeeStructure.objects.filter(
            class_assigned=student.class_assigned,
            academic_year=academic_year,
            student_type=student.student_type,
            category=category,
            is_active=True
        ).first()
        
        if fee_structure:
            if payment_period == 'FIRST':
                due_for_category = fee_structure.semester1_amount_lrd
            elif payment_period == 'SECOND':
                due_for_category = fee_structure.semester2_amount_lrd
            else:
                due_for_category = fee_structure.semester1_amount_lrd + fee_structure.semester2_amount_lrd
            
            # Calculate already paid
            already_paid = Decimal('0')
            receipts = Receipt.objects.filter(student=student, is_voided=False, is_legacy=False)
            for receipt in receipts:
                allocations = receipt.allocations.filter(fee_category=category)
                already_paid += sum(a.amount_lrd for a in allocations)
            
            remaining_due = due_for_category - already_paid
            
            # Amount to pay for this category (only the remaining due)
            pay_amount = min(amount, remaining_due)
            overpayment = amount - pay_amount
            
            # Create receipt
            receipt = Receipt.objects.create(
                student=student,
                payment_date=date.today(),
                amount_lrd=pay_amount,
                amount_usd=0,
                payment_method=request.POST.get('payment_method', 'CASH'),
                is_legacy=False,
            )
            
            # Allocation for this category
            PaymentAllocation.objects.create(
                receipt=receipt,
                fee_category=category,
                amount_lrd=pay_amount,
                amount_usd=0,
            )
            
            # Handle overpayment
            if overpayment > 0:
                if action == 'next_fee':
                    # Apply to next fee category (Tuition)
                    tuition_category = FeeCategory.objects.filter(code='TUI').first()
                    if tuition_category:
                        PaymentAllocation.objects.create(
                            receipt=receipt,
                            fee_category=tuition_category,
                            amount_lrd=overpayment,
                            amount_usd=0,
                        )
                        messages.info(request, f'✅ Payment recorded. {pay_amount} LRD applied to {category.name}. Extra {overpayment} LRD applied to Tuition.')
                    else:
                        messages.info(request, f'✅ Payment recorded. {pay_amount} LRD applied to {category.name}. Extra {overpayment} LRD recorded as credit.')
                elif action == 'credit':
                    # Record as credit (create a credit note)
                    messages.info(request, f'✅ Payment recorded. {pay_amount} LRD applied to {category.name}. Extra {overpayment} LRD available as credit for future payments.')
                else:  # refund or correct
                    messages.info(request, f'✅ Payment recorded. {pay_amount} LRD applied to {category.name}. Extra {overpayment} LRD not applied.')
            else:
                messages.success(request, f'✅ Receipt #{receipt.receipt_number} created successfully!')
            
            return redirect('receipt_print', receipt_id=receipt.id)
    
    return redirect('dashboard')








