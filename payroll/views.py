from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from datetime import date
from .models import Staff, StaffAdvance, PayrollPeriod, PayrollEntry, PayrollReceipt

@login_required
def staff_list(request):
    staff_members = Staff.objects.filter(is_active=True)
    return render(request, 'payroll/staff_list.html', {'staff_members': staff_members})

@login_required
def staff_add(request):
    if request.method == 'POST':
        staff = Staff.objects.create(
            name=request.POST.get('name'),
            position=request.POST.get('position'),
            staff_id=request.POST.get('staff_id'),
            monthly_salary_lrd=request.POST.get('monthly_salary_lrd', 0),
            monthly_salary_usd=request.POST.get('monthly_salary_usd', 0),
            phone=request.POST.get('phone', ''),
            email=request.POST.get('email', ''),
            hire_date=request.POST.get('hire_date'),
        )
        messages.success(request, f'Staff {staff.name} added successfully!')
        return redirect('staff_list')
    
    return render(request, 'payroll/staff_add.html')

@login_required
def staff_edit(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    
    if request.method == 'POST':
        staff.name = request.POST.get('name')
        staff.position = request.POST.get('position')
        staff.monthly_salary_lrd = request.POST.get('monthly_salary_lrd', 0)
        staff.monthly_salary_usd = request.POST.get('monthly_salary_usd', 0)
        staff.phone = request.POST.get('phone', '')
        staff.email = request.POST.get('email', '')
        staff.save()
        messages.success(request, 'Staff updated successfully!')
        return redirect('staff_list')
    
    return render(request, 'payroll/staff_edit.html', {'staff': staff})

@login_required
def staff_delete(request, pk):
    staff = get_object_or_404(Staff, pk=pk)
    if request.method == 'POST':
        staff.is_active = False
        staff.save()
        messages.success(request, 'Staff removed successfully!')
        return redirect('staff_list')
    
    return render(request, 'payroll/staff_delete.html', {'staff': staff})

@login_required

@login_required

@login_required
def staff_advance(request, staff_id):
    from datetime import datetime
    staff = get_object_or_404(Staff, pk=staff_id)
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    if request.method == 'POST':
        try:
            amount_lrd = float(request.POST.get('amount_lrd', 0) or 0)
            amount_usd = float(request.POST.get('amount_usd', 0) or 0)
            deduction_type = request.POST.get('deduction_type', 'ADVANCE')
            reason = request.POST.get('reason', '')
            month = int(request.POST.get('month', current_month))
            year = int(request.POST.get('year', current_year))
            
            if amount_lrd == 0 and amount_usd == 0:
                messages.error(request, 'Please enter an amount')
                return redirect('staff_advance', staff_id=staff.id)
            
            StaffAdvance.objects.create(
                staff=staff,
                deduction_type=deduction_type,
                month=month,
                year=year,
                amount_lrd=amount_lrd,
                amount_usd=amount_usd,
                reason=reason,
            )
            
            messages.success(request, f'{staff.name} - {dict(StaffAdvance.DEDUCTION_TYPES).get(deduction_type, "Deduction")} of {amount_lrd} LRD recorded for {month}/{year}!')
            return redirect('staff_list')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('staff_advance', staff_id=staff.id)
    
    context = {
        'staff': staff,
        'current_month': current_month,
        'current_year': current_year,
        'months': StaffAdvance.MONTH_CHOICES,
        'deduction_types': StaffAdvance.DEDUCTION_TYPES,
    }
    return render(request, 'payroll/staff_advance.html', context)

@login_required

@login_required

@login_required

@login_required

@login_required

@login_required

@login_required
def process_payroll(request):
    from datetime import datetime
    from decimal import Decimal
    import uuid
    
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    if request.method == 'POST':
        month = int(request.POST.get('month'))
        year = int(request.POST.get('year'))
        payment_type = request.POST.get('payment_type', 'bulk')
        staff_ids = request.POST.getlist('staff_ids') if payment_type == 'individual' else []
        
        # Show warning if processing different month
        if year < current_year or (year == current_year and month < current_month):
            messages.warning(request, f'⚠️ You are processing payroll for {month}/{year} (past month). Please verify this is correct.')
        elif year > current_year or (year == current_year and month > current_month):
            messages.warning(request, f'⚠️ You are processing payroll for {month}/{year} (future month). This is for advance payment only.')
        
        # Get or create payroll period
        payroll_period, created = PayrollPeriod.objects.get_or_create(
            month=month,
            year=year,
            defaults={
                'processed_by': request.user,
                'is_processed': False,
                'notes': f"Processed via {payment_type.upper()} payment"
            }
        )
        
        # Get staff members to process (excluding already paid staff)
        if payment_type == 'individual' and staff_ids:
            already_paid = PayrollEntry.objects.filter(
                payroll_period=payroll_period,
                staff_id__in=staff_ids
            ).values_list('staff_id', flat=True)
            
            staff_to_process = Staff.objects.filter(id__in=staff_ids, is_active=True).exclude(id__in=already_paid)
            
            if already_paid:
                paid_names = Staff.objects.filter(id__in=already_paid).values_list('name', flat=True)
                messages.warning(request, f'⚠️ The following staff were already paid for {month}/{year}: {", ".join(paid_names)}')
        else:
            already_paid = PayrollEntry.objects.filter(
                payroll_period=payroll_period
            ).values_list('staff_id', flat=True)
            
            staff_to_process = Staff.objects.filter(is_active=True).exclude(id__in=already_paid)
            
            if already_paid:
                paid_count = len(already_paid)
                messages.info(request, f'ℹ️ {paid_count} staff were already paid for {month}/{year}. Processing remaining staff.')
        
        if not staff_to_process.exists():
            messages.error(request, f'No eligible staff to process for {month}/{year}. All staff have already been paid.')
            return redirect('payroll_history' if payment_type == 'bulk' else 'staff_list')
        
        processed_entries = []
        
        with transaction.atomic():
            total_lrd = Decimal('0')
            total_usd = Decimal('0')
            processed_count = 0
            
            for staff in staff_to_process:
                # Get deductions for this specific month and year
                deductions = StaffAdvance.objects.filter(
                    staff=staff,
                    month=month,
                    year=year,
                    is_applied=False
                )
                
                deduction_lrd = sum(Decimal(str(d.amount_lrd)) for d in deductions)
                deduction_usd = sum(Decimal(str(d.amount_usd)) for d in deductions)
                deduction_reason = "; ".join([f"{d.get_deduction_type_display()}: {d.reason}" for d in deductions if d.reason])
                
                # Mark deductions as applied
                for deduction in deductions:
                    deduction.is_applied = True
                    deduction.save()
                
                net_pay_lrd = Decimal(str(staff.monthly_salary_lrd)) - deduction_lrd
                net_pay_usd = Decimal(str(staff.monthly_salary_usd)) - deduction_usd
                
                payroll_entry = PayrollEntry.objects.create(
                    payroll_period=payroll_period,
                    staff=staff,
                    base_salary_lrd=staff.monthly_salary_lrd,
                    base_salary_usd=staff.monthly_salary_usd,
                    deduction_lrd=deduction_lrd,
                    deduction_usd=deduction_usd,
                    deduction_reason=deduction_reason,
                    net_pay_lrd=max(net_pay_lrd, Decimal('0')),
                    net_pay_usd=max(net_pay_usd, Decimal('0')),
                )
                
                # Generate receipt for each staff
                receipt_number = f"PY-{year}{month:02d}-{staff.staff_id}-{uuid.uuid4().hex[:6].upper()}"
                PayrollReceipt.objects.create(
                    payroll_entry=payroll_entry,
                    receipt_number=receipt_number,
                    printed_by=request.user
                )
                
                processed_entries.append(payroll_entry)
                
                total_lrd += max(net_pay_lrd, Decimal('0'))
                total_usd += max(net_pay_usd, Decimal('0'))
                processed_count += 1
            
            # Update payroll period totals
            payroll_period.total_amount_lrd = Decimal(str(payroll_period.total_amount_lrd)) + total_lrd
            payroll_period.total_amount_usd = Decimal(str(payroll_period.total_amount_usd)) + total_usd
            payroll_period.is_processed = True
            payroll_period.save()
        
        messages.success(request, f'✅ Payroll for {month}/{year} processed successfully! Processed {processed_count} staff. Total: {total_lrd:,.2f} LRD / {total_usd:,.2f} USD')
        
        # Store processed entries in session for bulk receipt printing
        request.session['bulk_payroll_entries'] = [e.id for e in processed_entries]
        request.session['bulk_payroll_period'] = payroll_period.id
        
        # Ask user how they want to print receipts
        return render(request, 'payroll/bulk_receipt_options.html', {
            'processed_count': processed_count,
            'payroll_period': payroll_period,
            'entries': processed_entries
        })
    
    staff_members = Staff.objects.filter(is_active=True)
    context = {
        'current_month': current_month,
        'current_year': current_year,
        'months': PayrollPeriod.MONTH_CHOICES,
        'staff_members': staff_members,
    }
    return render(request, 'payroll/process_payroll.html', context)

@login_required
def payroll_history(request):
    payroll_periods = PayrollPeriod.objects.all()
    return render(request, 'payroll/payroll_history.html', {'payroll_periods': payroll_periods})

@login_required
def payroll_detail(request, pk):
    payroll = get_object_or_404(PayrollPeriod, pk=pk)
    entries = payroll.entries.all().select_related('staff')
    return render(request, 'payroll/payroll_detail.html', {'payroll': payroll, 'entries': entries})



@login_required

@login_required

@login_required

@login_required
def pay_staff_individual(request, staff_id):
    """Process payroll for a single staff member and generate receipt"""
    from datetime import datetime
    from decimal import Decimal
    import uuid
    
    staff = get_object_or_404(Staff, pk=staff_id)
    current_month = datetime.now().month
    current_year = datetime.now().year
    
    if request.method == 'POST':
        month = int(request.POST.get('month'))
        year = int(request.POST.get('year'))
        
        # Check if this staff was already paid for this month
        payroll_period, created = PayrollPeriod.objects.get_or_create(
            month=month,
            year=year,
            defaults={
                'processed_by': request.user,
                'is_processed': False
            }
        )
        
        existing_entry = PayrollEntry.objects.filter(payroll_period=payroll_period, staff=staff).first()
        if existing_entry:
            messages.error(request, f'{staff.name} has already been paid for {month}/{year}!')
            return redirect('staff_list')
        
        # Show warning if processing different month
        if year < current_year or (year == current_year and month < current_month):
            messages.warning(request, f'⚠️ You are processing payroll for {month}/{year} (past month). Please verify this is correct.')
        elif year > current_year or (year == current_year and month > current_month):
            messages.warning(request, f'⚠️ You are processing payroll for {month}/{year} (future month). This is for advance payment only.')
        
        with transaction.atomic():
            # Get deductions for this specific month and year
            deductions = StaffAdvance.objects.filter(
                staff=staff,
                month=month,
                year=year,
                is_applied=False
            )
            
            deduction_lrd = sum(Decimal(str(d.amount_lrd)) for d in deductions)
            deduction_usd = sum(Decimal(str(d.amount_usd)) for d in deductions)
            deduction_reason = "; ".join([f"{d.get_deduction_type_display()}: {d.reason}" for d in deductions if d.reason])
            
            # Mark deductions as applied
            for deduction in deductions:
                deduction.is_applied = True
                deduction.save()
            
            net_pay_lrd = Decimal(str(staff.monthly_salary_lrd)) - deduction_lrd
            net_pay_usd = Decimal(str(staff.monthly_salary_usd)) - deduction_usd
            
            payroll_entry = PayrollEntry.objects.create(
                payroll_period=payroll_period,
                staff=staff,
                base_salary_lrd=staff.monthly_salary_lrd,
                base_salary_usd=staff.monthly_salary_usd,
                deduction_lrd=deduction_lrd,
                deduction_usd=deduction_usd,
                deduction_reason=deduction_reason,
                net_pay_lrd=max(net_pay_lrd, Decimal('0')),
                net_pay_usd=max(net_pay_usd, Decimal('0')),
            )
            
            # Generate receipt
            receipt_number = f"PY-{year}{month:02d}-{staff.staff_id}-{uuid.uuid4().hex[:6].upper()}"
            PayrollReceipt.objects.create(
                payroll_entry=payroll_entry,
                receipt_number=receipt_number,
                printed_by=request.user
            )
            
            # Update payroll period totals
            payroll_period.total_amount_lrd = Decimal(str(payroll_period.total_amount_lrd)) + max(net_pay_lrd, Decimal('0'))
            payroll_period.total_amount_usd = Decimal(str(payroll_period.total_amount_usd)) + max(net_pay_usd, Decimal('0'))
            payroll_period.is_processed = True
            payroll_period.save()
        
        messages.success(request, f'✅ Payroll processed for {staff.name} - {month}/{year}! Net Pay: {net_pay_lrd:,.2f} LRD / {net_pay_usd:,.2f} USD')
        
        # Redirect to receipt print page
        return redirect('payroll_receipt_print', entry_id=payroll_entry.id)
    
    context = {
        'staff': staff,
        'current_month': current_month,
        'current_year': current_year,
        'months': PayrollPeriod.MONTH_CHOICES,
    }
    return render(request, 'payroll/pay_staff_individual.html', context)








@login_required
def payroll_receipt_print(request, entry_id):
    """Print payroll receipt"""
    from decimal import Decimal
    
    entry = get_object_or_404(PayrollEntry, id=entry_id)
    receipt = PayrollReceipt.objects.filter(payroll_entry=entry).first()
    
    context = {
        'entry': entry,
        'receipt': receipt,
        'staff': entry.staff,
        'payroll_period': entry.payroll_period,
    }
    return render(request, 'payroll/receipt_print.html', context)


@login_required
def payroll_bulk_receipts_print(request, period_id):
    """Print summary sheet for bulk payroll (all staff on one page)"""
    from decimal import Decimal
    
    payroll_period = get_object_or_404(PayrollPeriod, id=period_id)
    entries = payroll_period.entries.all().select_related('staff')
    
    total_lrd = sum(float(e.net_pay_lrd) for e in entries)
    total_usd = sum(float(e.net_pay_usd) for e in entries)
    
    context = {
        'payroll_period': payroll_period,
        'entries': entries,
        'total_lrd': total_lrd,
        'total_usd': total_usd,
    }
    return render(request, 'payroll/bulk_summary_print.html', context)

@login_required
def payroll_bulk_individual_receipts(request, period_id):
    """Print individual receipts for each staff in bulk payroll"""
    payroll_period = get_object_or_404(PayrollPeriod, id=period_id)
    entries = payroll_period.entries.all().select_related('staff')
    
    context = {
        'payroll_period': payroll_period,
        'entries': entries,
    }
    return render(request, 'payroll/bulk_individual_receipts.html', context)


@login_required
def staff_payroll_history(request, staff_id):
    """View payroll history for a specific staff member"""
    staff = get_object_or_404(Staff, pk=staff_id)
    payroll_entries = PayrollEntry.objects.filter(staff=staff).select_related('payroll_period').order_by('-payroll_period__year', '-payroll_period__month')
    
    # Calculate totals
    total_paid_lrd = sum(float(e.net_pay_lrd) for e in payroll_entries)
    total_paid_usd = sum(float(e.net_pay_usd) for e in payroll_entries)
    total_deductions_lrd = sum(float(e.deduction_lrd) for e in payroll_entries)
    total_deductions_usd = sum(float(e.deduction_usd) for e in payroll_entries)
    
    context = {
        'staff': staff,
        'payroll_entries': payroll_entries,
        'total_paid_lrd': total_paid_lrd,
        'total_paid_usd': total_paid_usd,
        'total_deductions_lrd': total_deductions_lrd,
        'total_deductions_usd': total_deductions_usd,
    }
    return render(request, 'payroll/staff_payroll_history.html', context)
