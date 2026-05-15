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
    if request.method == 'POST':
        try:
            student = Student.objects.create(
                admission_number=request.POST.get('admission_number'),
                first_name=request.POST.get('first_name'),
                last_name=request.POST.get('last_name'),
                class_assigned_id=request.POST.get('class_assigned') or None,
                student_type=request.POST.get('student_type', 'NEW'),
                parent_name=request.POST.get('parent_name', ''),
                parent_phone=request.POST.get('parent_phone', ''),
                parent_phone_alternative=request.POST.get('parent_phone_alternative', ''),
                address=request.POST.get('address', ''),
                notes=request.POST.get('notes', ''),
            )
            messages.success(request, f'Student {student.full_name} added successfully!')
            return redirect('student_detail', pk=student.id)
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    classes = Class.objects.filter(is_active=True).order_by('name')
    return render(request, 'students/add.html', {'classes': classes})

@login_required
def student_detail(request, pk):
    student = get_object_or_404(Student, pk=pk)
    
    # Get fee ledger for this student (most recent)
    ledger = StudentFeeLedger.objects.filter(student=student).first()
    
    # Calculate balances
    if ledger:
        semester1_balance_lrd = ledger.semester1_total_lrd - ledger.semester1_paid_lrd
        semester1_balance_usd = ledger.semester1_total_usd - ledger.semester1_paid_usd
        semester2_balance_lrd = ledger.semester2_total_lrd - ledger.semester2_paid_lrd
        semester2_balance_usd = ledger.semester2_total_usd - ledger.semester2_paid_usd
        total_balance_lrd = semester1_balance_lrd + semester2_balance_lrd
        total_balance_usd = semester1_balance_usd + semester2_balance_usd
        total_due_lrd = (ledger.semester1_total_lrd + ledger.semester2_total_lrd)
        total_due_usd = (ledger.semester1_total_usd + ledger.semester2_total_usd)
    else:
        semester1_balance_lrd = 0
        semester1_balance_usd = 0
        semester2_balance_lrd = 0
        semester2_balance_usd = 0
        total_balance_lrd = 0
        total_balance_usd = 0
        total_due_lrd = 0
        total_due_usd = 0
    
    # Get all receipts
    receipts = Receipt.objects.filter(student=student, is_voided=False).order_by('-payment_date')
    
    # Calculate total paid
    total_paid_lrd = receipts.aggregate(Sum('amount_lrd'))['amount_lrd__sum'] or 0
    total_paid_usd = receipts.aggregate(Sum('amount_usd'))['amount_usd__sum'] or 0
    
    context = {
        'student': student,
        'current_balance_lrd': total_balance_lrd,
        'current_balance_usd': total_balance_usd,
        'total_due_lrd': total_due_lrd,
        'total_due_usd': total_due_usd,
        'total_paid_lrd': total_paid_lrd,
        'total_paid_usd': total_paid_usd,
        'receipts': receipts,
        'semester1_balance_lrd': semester1_balance_lrd,
        'semester1_balance_usd': semester1_balance_usd,
        'semester2_balance_lrd': semester2_balance_lrd,
        'semester2_balance_usd': semester2_balance_usd,
    }
    return render(request, 'students/detail.html', context)

@login_required
def student_edit(request, pk):
    student = get_object_or_404(Student, pk=pk)
    classes = Class.objects.filter(is_active=True).order_by('name')
    
    if request.method == 'POST':
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



