from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from .models import Student, Class
from fees.models import StudentFeeLedger
from receipts.models import Receipt

@login_required
def student_list(request):
    query = request.GET.get('q', '')
    students = Student.objects.filter(is_active=True)
    
    if query:
        students = students.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(admission_number__icontains=query) |
            Q(parent_phone__icontains=query)
        )
    
    paginator = Paginator(students, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'students/list.html', {'students': page_obj, 'query': query})

@login_required
def student_add(request):
    from fees.models import FeeStructure, StudentFeeLedger
    from fees.views import get_active_academic_year
    
    if request.method == 'POST':
        try:
            # Get form data with proper defaults
            admission_number = request.POST.get('admission_number', '').strip()
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            class_assigned_id = request.POST.get('class_assigned')
            student_type = request.POST.get('student_type', 'NEW')
            parent_name = request.POST.get('parent_name', '').strip()
            parent_phone = request.POST.get('parent_phone', '').strip()
            parent_phone_alternative = request.POST.get('parent_phone_alternative', '').strip()
            address = request.POST.get('address', '').strip()
            notes = request.POST.get('notes', '').strip()
            
            # Validate required fields
            if not admission_number:
                messages.error(request, 'Admission number is required')
                classes = Class.objects.filter(is_active=True).order_by('name')
                return render(request, 'students/add.html', {'classes': classes})
            
            if not first_name or not last_name:
                messages.error(request, 'First name and last name are required')
                classes = Class.objects.filter(is_active=True).order_by('name')
                return render(request, 'students/add.html', {'classes': classes})
            
            # Create student
            student = Student.objects.create(
                admission_number=admission_number,
                first_name=first_name,
                last_name=last_name,
                class_assigned_id=class_assigned_id if class_assigned_id else None,
                student_type=student_type,
                parent_name=parent_name,
                parent_phone=parent_phone,
                parent_phone_alternative=parent_phone_alternative,
                address=address,
                notes=notes,
            )
            
            # Auto-assign fees
            academic_year = get_active_academic_year()
            
            if student.class_assigned:
                fee_structures = FeeStructure.objects.filter(
                    class_assigned=student.class_assigned,
                    academic_year=academic_year,
                    student_type=student.student_type,
                    is_active=True
                )
                
                if fee_structures.exists():
                    semester1_total_lrd = sum(float(f.semester1_amount_lrd) for f in fee_structures)
                    semester1_total_usd = sum(float(f.semester1_amount_usd) for f in fee_structures)
                    semester2_total_lrd = sum(float(f.semester2_amount_lrd) for f in fee_structures)
                    semester2_total_usd = sum(float(f.semester2_amount_usd) for f in fee_structures)
                    
                    StudentFeeLedger.objects.create(
                        student=student,
                        academic_year=academic_year,
                        semester1_total_lrd=semester1_total_lrd,
                        semester1_total_usd=semester1_total_usd,
                        semester2_total_lrd=semester2_total_lrd,
                        semester2_total_usd=semester2_total_usd,
                    )
                    
                    messages.success(request, f'Student {student.full_name} added successfully with fees!')
                else:
                    messages.warning(request, f'Student added but no fee structure found. Please set up fees first.')
            else:
                messages.warning(request, f'Student added but no class assigned. Please assign a class.')
            
            return redirect('student_detail', pk=student.id)
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            classes = Class.objects.filter(is_active=True).order_by('name')
            return render(request, 'students/add.html', {'classes': classes})
    
    classes = Class.objects.filter(is_active=True).order_by('name')
    return render(request, 'students/add.html', {'classes': classes})

@login_required
def student_detail(request, pk):
    from fees.models import FeeCategory, FeeStructure, StudentFeeLedger, StudentScholarship
    from receipts.models import Receipt, PaymentAllocation
    from decimal import Decimal
    
    student = get_object_or_404(Student, pk=pk)
    
    # Get active fee categories
    fee_categories = FeeCategory.objects.filter(is_active=True)
    
    # Get current academic year
    from fees.views import get_active_academic_year
    academic_year = get_active_academic_year()
    
    # Get fee structure for this student
    fee_structures = FeeStructure.objects.filter(
        class_assigned=student.class_assigned,
        academic_year=academic_year,
        student_type=student.student_type,
        is_active=True
    ).select_related('category')
    
    # Get or create fee ledger
    ledger, created = StudentFeeLedger.objects.get_or_create(
        student=student,
        academic_year=academic_year,
        defaults={
            'semester1_total_lrd': 0,
            'semester1_total_usd': 0,
            'semester2_total_lrd': 0,
            'semester2_total_usd': 0,
            'semester1_paid_lrd': 0,
            'semester1_paid_usd': 0,
            'semester2_paid_lrd': 0,
            'semester2_paid_usd': 0,
            'discount_applied_lrd': 0,
            'discount_applied_usd': 0,
        }
    )
    
    # Get all receipts for this student
    receipts = Receipt.objects.filter(student=student, is_voided=False).order_by('-payment_date')
    
    # Get scholarship and its selected categories
    scholarship = StudentScholarship.objects.filter(student=student, academic_year=academic_year, is_active=True).first()
    
    # Get the category IDs that the scholarship applies to
    scholarship_category_ids = []
    if scholarship:
        scholarship_category_ids = list(scholarship.scholarship.applies_to_categories.values_list('id', flat=True))
    
    # Build fee breakdown
    fee_breakdown = []
    total_sem1_due_lrd = Decimal('0')
    total_sem1_due_usd = Decimal('0')
    total_sem1_paid_lrd = Decimal('0')
    total_sem1_paid_usd = Decimal('0')
    total_sem2_due_lrd = Decimal('0')
    total_sem2_due_usd = Decimal('0')
    total_sem2_paid_lrd = Decimal('0')
    total_sem2_paid_usd = Decimal('0')
    total_due_lrd = Decimal('0')
    total_due_usd = Decimal('0')
    total_paid_lrd = Decimal('0')
    total_paid_usd = Decimal('0')
    
    # Calculate total original fees for categories that receive scholarship (for LRD)
    total_eligible_lrd = Decimal('0')
    total_eligible_usd = Decimal('0')
    
    for fs in fee_structures:
        # Check if this category is eligible for scholarship
        if scholarship_category_ids and fs.category.id not in scholarship_category_ids:
            # This category does NOT receive scholarship - use full amount
            continue
        
        # This category receives scholarship
        total_eligible_lrd += fs.semester1_amount_lrd + fs.semester2_amount_lrd
        total_eligible_usd += fs.semester1_amount_usd + fs.semester2_amount_usd
    
    for category in fee_categories:
        fs = fee_structures.filter(category=category).first()
        
        # Check if this category is eligible for scholarship
        is_eligible = False
        if scholarship:
            is_eligible = (category.id in scholarship_category_ids)
        
        if fs:
            sem1_due_lrd = fs.semester1_amount_lrd or Decimal('0')
            sem2_due_lrd = fs.semester2_amount_lrd or Decimal('0')
            sem1_due_usd = fs.semester1_amount_usd or Decimal('0')
            sem2_due_usd = fs.semester2_amount_usd or Decimal('0')
            
            # Apply discount ONLY if this category is eligible
            if is_eligible and scholarship:
                # Apply 50% discount to this category's fees
                sem1_due_lrd = sem1_due_lrd / 2
                sem2_due_lrd = sem2_due_lrd / 2
                sem1_due_usd = sem1_due_usd / 2
                sem2_due_usd = sem2_due_usd / 2
            
            # Calculate paid amounts from receipts
            sem1_paid_lrd = Decimal('0')
            sem1_paid_usd = Decimal('0')
            sem2_paid_lrd = Decimal('0')
            sem2_paid_usd = Decimal('0')
            
            for receipt in receipts:
                if not receipt.is_legacy:
                    allocations = receipt.allocations.filter(fee_category=category)
                    for alloc in allocations:
                        if receipt.payment_period == 'FIRST':
                            sem1_paid_lrd += alloc.amount_lrd or Decimal('0')
                            sem1_paid_usd += alloc.amount_usd or Decimal('0')
                        elif receipt.payment_period == 'SECOND':
                            sem2_paid_lrd += alloc.amount_lrd or Decimal('0')
                            sem2_paid_usd += alloc.amount_usd or Decimal('0')
                        else:
                            sem1_paid_lrd += (alloc.amount_lrd or Decimal('0')) / 2
                            sem2_paid_lrd += (alloc.amount_lrd or Decimal('0')) / 2
                            sem1_paid_usd += (alloc.amount_usd or Decimal('0')) / 2
                            sem2_paid_usd += (alloc.amount_usd or Decimal('0')) / 2
            
            total_due_category_lrd = sem1_due_lrd + sem2_due_lrd
            total_due_category_usd = sem1_due_usd + sem2_due_usd
            total_paid_category_lrd = sem1_paid_lrd + sem2_paid_lrd
            total_paid_category_usd = sem1_paid_usd + sem2_paid_usd
            
            fee_breakdown.append({
                'category': category,
                'sem1_due_lrd': float(sem1_due_lrd),
                'sem1_due_usd': float(sem1_due_usd),
                'sem1_paid_lrd': float(sem1_paid_lrd),
                'sem1_paid_usd': float(sem1_paid_usd),
                'sem2_due_lrd': float(sem2_due_lrd),
                'sem2_due_usd': float(sem2_due_usd),
                'sem2_paid_lrd': float(sem2_paid_lrd),
                'sem2_paid_usd': float(sem2_paid_usd),
                'total_due_lrd': float(total_due_category_lrd),
                'total_due_usd': float(total_due_category_usd),
                'total_paid_lrd': float(total_paid_category_lrd),
                'total_paid_usd': float(total_paid_category_usd),
            })
            
            total_sem1_due_lrd += sem1_due_lrd
            total_sem1_due_usd += sem1_due_usd
            total_sem1_paid_lrd += sem1_paid_lrd
            total_sem1_paid_usd += sem1_paid_usd
            total_sem2_due_lrd += sem2_due_lrd
            total_sem2_due_usd += sem2_due_usd
            total_sem2_paid_lrd += sem2_paid_lrd
            total_sem2_paid_usd += sem2_paid_usd
            total_due_lrd += total_due_category_lrd
            total_due_usd += total_due_category_usd
            total_paid_lrd += total_paid_category_lrd
            total_paid_usd += total_paid_category_usd
        else:
            fee_breakdown.append({
                'category': category,
                'sem1_due_lrd': 0,
                'sem1_due_usd': 0,
                'sem1_paid_lrd': 0,
                'sem1_paid_usd': 0,
                'sem2_due_lrd': 0,
                'sem2_due_usd': 0,
                'sem2_paid_lrd': 0,
                'sem2_paid_usd': 0,
                'total_due_lrd': 0,
                'total_due_usd': 0,
                'total_paid_lrd': 0,
                'total_paid_usd': 0,
            })
    
    # Convert totals to float
    total_due_lrd_float = float(total_due_lrd)
    total_due_usd_float = float(total_due_usd)
    total_paid_lrd_float = float(total_paid_lrd)
    total_paid_usd_float = float(total_paid_usd)
    
    # Calculate scholarship discount (for display)
    discount_lrd = float(ledger.discount_applied_lrd) if ledger.discount_applied_lrd else 0
    discount_usd = float(ledger.discount_applied_usd) if ledger.discount_applied_usd else 0
    
    # Calculate scholarship percentage
    scholarship_percent = 0
    if scholarship and scholarship.scholarship.is_percentage:
        scholarship_percent = float(scholarship.scholarship.discount_value)
    
    remaining_balance_lrd = total_due_lrd_float - total_paid_lrd_float
    remaining_balance_usd = total_due_usd_float - total_paid_usd_float
    
    total_balance_lrd = total_due_lrd_float - total_paid_lrd_float
    total_balance_usd = total_due_usd_float - total_paid_usd_float
    
    scholarship_name = scholarship.scholarship.name if scholarship else None
    scholarship_discount = float(scholarship.scholarship.discount_value) if scholarship else 0
    
    context = {
        'student': student,
        'fee_breakdown': fee_breakdown,
        'receipts': receipts,
        'total_due_lrd': total_due_lrd_float,
        'total_due_usd': total_due_usd_float,
        'total_paid_lrd': total_paid_lrd_float,
        'total_paid_usd': total_paid_usd_float,
        'total_balance_lrd': total_balance_lrd,
        'total_balance_usd': total_balance_usd,
        'total_sem1_due_lrd': float(total_sem1_due_lrd),
        'total_sem1_due_usd': float(total_sem1_due_usd),
        'total_sem1_paid_lrd': float(total_sem1_paid_lrd),
        'total_sem1_paid_usd': float(total_sem1_paid_usd),
        'total_sem2_due_lrd': float(total_sem2_due_lrd),
        'total_sem2_due_usd': float(total_sem2_due_usd),
        'total_sem2_paid_lrd': float(total_sem2_paid_lrd),
        'total_sem2_paid_usd': float(total_sem2_paid_usd),
        'discount_lrd': discount_lrd,
        'discount_usd': discount_usd,
        'scholarship_percent': scholarship_percent,
        'remaining_balance_lrd': remaining_balance_lrd,
        'remaining_balance_usd': remaining_balance_usd,
        'scholarship_name': scholarship_name,
        'scholarship_discount': scholarship_discount,
        'has_scholarship': scholarship is not None,
    }
    return render(request, 'students/detail.html', context)
@login_required
def student_edit(request, pk):
    from fees.models import FeeStructure, StudentFeeLedger
    from fees.views import get_active_academic_year
    
    student = get_object_or_404(Student, pk=pk)
    classes = Class.objects.filter(is_active=True).order_by('name')
    
    if request.method == 'POST':
        # Save old values to check if class or student type changed
        old_class = student.class_assigned
        old_student_type = student.student_type
        
        student.first_name = request.POST.get('first_name')
        student.last_name = request.POST.get('last_name')
        student.class_assigned_id = request.POST.get('class_assigned') or None
        student.student_type = request.POST.get('student_type', 'NEW')
        student.parent_name = request.POST.get('parent_name', '')
        student.parent_phone = request.POST.get('parent_phone', '')
        student.parent_phone_alternative = request.POST.get('parent_phone_alternative', '')
        student.address = request.POST.get('address', '')
        student.notes = request.POST.get('notes', '')
        student.save()
        
        # If class or student type changed, reassign fees
        if old_class != student.class_assigned or old_student_type != student.student_type:
            academic_year = get_active_academic_year()
            
            if student.class_assigned:
                fee_structures = FeeStructure.objects.filter(
                    class_assigned=student.class_assigned,
                    academic_year=academic_year,
                    student_type=student.student_type,
                    is_active=True
                )
                
                if fee_structures.exists():
                    semester1_total_lrd = sum(float(f.semester1_amount_lrd) for f in fee_structures)
                    semester1_total_usd = sum(float(f.semester1_amount_usd) for f in fee_structures)
                    semester2_total_lrd = sum(float(f.semester2_amount_lrd) for f in fee_structures)
                    semester2_total_usd = sum(float(f.semester2_amount_usd) for f in fee_structures)
                    
                    ledger, created = StudentFeeLedger.objects.get_or_create(
                        student=student,
                        academic_year=academic_year,
                        defaults={
                            'semester1_total_lrd': semester1_total_lrd,
                            'semester1_total_usd': semester1_total_usd,
                            'semester2_total_lrd': semester2_total_lrd,
                            'semester2_total_usd': semester2_total_usd,
                        }
                    )
                    
                    if not created:
                        ledger.semester1_total_lrd = semester1_total_lrd
                        ledger.semester1_total_usd = semester1_total_usd
                        ledger.semester2_total_lrd = semester2_total_lrd
                        ledger.semester2_total_usd = semester2_total_usd
                        ledger.save()
        
        messages.success(request, 'Student updated successfully!')
        return redirect('student_detail', pk=student.id)
    
    return render(request, 'students/edit.html', {'student': student, 'classes': classes})
@login_required
def student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == 'POST':
        student.is_active = False
        student.save()
        messages.success(request, 'Student removed successfully!')
        return redirect('student_list')
    
    return render(request, 'students/delete.html', {'student': student})

@login_required
def class_list(request):
    """List all classes"""
    classes = Class.objects.filter(is_active=True).order_by('name')
    return render(request, 'students/class_list.html', {'classes': classes})

@login_required
@login_required
def class_add(request):
    """Add new class with validation"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        section = request.POST.get('section', '').strip()
        
        # Validate class name
        if not name:
            messages.error(request, '❌ Class name is required. Please enter a class name.')
            return render(request, 'students/class_add.html')
        
        # Check if class with same name and section already exists
        existing_class = Class.objects.filter(name=name, section=section).first()
        
        if existing_class:
            if section:
                messages.error(request, f'❌ Class "{name} - {section}" already exists! Please use a different section or class name.')
            else:
                messages.error(request, f'❌ Class "{name}" already exists! Please use a different class name or add a section (e.g., {name} - A).')
            return render(request, 'students/class_add.html')
        
        # Create the new class
        try:
            new_class = Class.objects.create(name=name, section=section)
            if section:
                messages.success(request, f'✅ Class "{name} - {section}" added successfully!')
            else:
                messages.success(request, f'✅ Class "{name}" added successfully!')
            return redirect('class_list')
        except Exception as e:
            messages.error(request, f'❌ Error creating class: {str(e)}')
            return render(request, 'students/class_add.html')
    
    return render(request, 'students/class_add.html')

@login_required
@login_required
def class_edit(request, pk):
    """Edit class"""
    class_obj = get_object_or_404(Class, pk=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        section = request.POST.get('section', '').strip()
        
        if not name:
            messages.error(request, '❌ Class name is required.')
            return render(request, 'students/class_edit.html', {'class': class_obj})
        
        # Check if another class with same name and section exists (excluding current)
        existing_class = Class.objects.filter(name=name, section=section).exclude(id=class_obj.id).first()
        
        if existing_class:
            if section:
                messages.error(request, f'❌ Class "{name} - {section}" already exists! Please use a different section.')
            else:
                messages.error(request, f'❌ Class "{name}" already exists! Please use a different name.')
            return render(request, 'students/class_edit.html', {'class': class_obj})
        
        # Update the class
        class_obj.name = name
        class_obj.section = section
        class_obj.save()
        
        messages.success(request, '✅ Class updated successfully!')
        return redirect('class_list')
    
    return render(request, 'students/class_edit.html', {'class': class_obj})

@login_required
def class_delete(request, pk):
    """Delete class (soft delete)"""
    class_obj = get_object_or_404(Class, pk=pk)
    
    if request.method == 'POST':
        class_obj.is_active = False
        class_obj.save()
        messages.success(request, 'Class removed successfully!')
        return redirect('class_list')
    
    return render(request, 'students/class_delete.html', {'class': class_obj})



