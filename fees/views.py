from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from datetime import date, timedelta
from django.db.models import Q, Sum

from students.models import Student, Class
from .models import (
    AcademicSession,
    FeeCategory,
    FeeStructure,
    InstallmentPlan,
    StudentFeeLedger,
    InstallmentReminder,
    ScholarshipType,
    StudentScholarship
)

def get_active_academic_year():
    """Get the currently active academic year"""
    active_session = AcademicSession.objects.filter(is_active=True).first()
    if active_session:
        return active_session.academic_year
    # Default to current year if none active
    return "2024-2025"

def get_active_semester():
    """Get the currently active semester"""
    active_session = AcademicSession.objects.filter(is_active=True).first()
    if active_session:
        return active_session.current_semester
    return 'FIRST'

# ============ FEE STRUCTURE MATRIX ============

@login_required
def fee_structure_matrix(request):
    """Matrix view for setting fees with Yearly, Sem1, Sem2 per category"""
    classes = Class.objects.filter(is_active=True)
    categories = FeeCategory.objects.filter(is_active=True)
    academic_year = request.GET.get('academic_year', get_active_academic_year())
    
    # Get or create fee structures for display
    fee_matrix = {}
    for class_obj in classes:
        fee_matrix[class_obj.id] = {}
        for student_type in ['NEW', 'OLD']:
            fee_matrix[class_obj.id][student_type] = {}
            for category in categories:
                fee_struct, created = FeeStructure.objects.get_or_create(
                    class_assigned=class_obj,
                    academic_year=academic_year,
                    student_type=student_type,
                    category=category,
                    defaults={
                        'semester1_amount_lrd': 0,
                        'semester1_amount_usd': 0,
                        'semester2_amount_lrd': 0,
                        'semester2_amount_usd': 0,
                    }
                )
                
                fee_matrix[class_obj.id][student_type][category.id] = {
                    'sem1_lrd': fee_struct.semester1_amount_lrd,
                    'sem1_usd': fee_struct.semester1_amount_usd,
                    'sem2_lrd': fee_struct.semester2_amount_lrd,
                    'sem2_usd': fee_struct.semester2_amount_usd,
                }
    
    if request.method == 'POST':
        for key, value in request.POST.items():
            if key.startswith('fee_'):
                parts = key.split('_')
                if len(parts) >= 6:
                    class_id = parts[1]
                    student_type = parts[2]
                    category_id = parts[3]
                    period = parts[4]
                    currency = parts[5]
                    amount = float(value) if value else 0
                    
                    fee, created = FeeStructure.objects.get_or_create(
                        class_assigned_id=class_id,
                        academic_year=academic_year,
                        student_type=student_type,
                        category_id=category_id,
                        defaults={
                            'semester1_amount_lrd': 0,
                            'semester1_amount_usd': 0,
                            'semester2_amount_lrd': 0,
                            'semester2_amount_usd': 0,
                        }
                    )
                    
                    if period == 'sem1':
                        if currency == 'LRD':
                            fee.semester1_amount_lrd = amount
                        else:
                            fee.semester1_amount_usd = amount
                    elif period == 'sem2':
                        if currency == 'LRD':
                            fee.semester2_amount_lrd = amount
                        else:
                            fee.semester2_amount_usd = amount
                    
                    fee.save()
        
        messages.success(request, 'Fee structure saved successfully!')
        return redirect(f'/fees/fee-matrix/?academic_year={academic_year}')
    
    available_years = ['2024-2025', '2025-2026', '2026-2027', '2027-2028']
    active_year = get_active_academic_year()
    
    context = {
        'classes': classes,
        'categories': categories,
        'academic_year': academic_year,
        'student_types': ['NEW', 'OLD'],
        'fee_matrix': fee_matrix,
        'available_years': available_years,
        'active_year': active_year,
    }
    return render(request, 'fees/fee_matrix.html', context)

# ============ INSTALLMENT PLANS ============

@login_required
def installment_plans(request):
    """Manage installment plans"""
    classes = Class.objects.filter(is_active=True)
    installment_plans = InstallmentPlan.objects.filter(is_active=True).select_related('class_assigned')
    
    if request.method == 'POST':
        try:
            InstallmentPlan.objects.create(
                class_assigned_id=request.POST.get('class_assigned'),
                academic_year=request.POST.get('academic_year', get_active_academic_year()),
                semester=request.POST.get('semester'),
                installment_number=request.POST.get('installment_number'),
                due_date=request.POST.get('due_date'),
                percentage=request.POST.get('percentage'),
                description=request.POST.get('description', ''),
            )
            messages.success(request, 'Installment plan added successfully!')
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
        return redirect('installment_plans')
    
    context = {
        'classes': classes,
        'installment_plans': installment_plans,
    }
    return render(request, 'fees/installments.html', context)

# ============ ACADEMIC SESSIONS ============

@login_required
def academic_session_settings(request):
    """Manage academic years and active semester"""
    sessions = AcademicSession.objects.all().order_by('-academic_year')
    
    if request.method == 'POST':
        if 'activate_session' in request.POST:
            session_id = request.POST.get('session_id')
            AcademicSession.objects.update(is_active=False)
            session = AcademicSession.objects.get(id=session_id)
            session.is_active = True
            session.save()
            messages.success(request, f'Activated {session.name}')
        elif 'set_semester' in request.POST:
            session_id = request.POST.get('session_id')
            semester = request.POST.get('semester')
            session = AcademicSession.objects.get(id=session_id)
            session.current_semester = semester
            session.save()
            messages.success(request, f'Semester updated to {session.get_current_semester_display()}')
        
        return redirect('academic_session_settings')
    
    context = {'sessions': sessions}
    return render(request, 'fees/academic_sessions.html', context)

@login_required
def add_academic_session(request):
    if request.method == 'POST':
        AcademicSession.objects.create(
            name=request.POST.get('name'),
            academic_year=request.POST.get('academic_year'),
            start_date=request.POST.get('start_date'),
            end_date=request.POST.get('end_date'),
            current_semester=request.POST.get('current_semester', 'FIRST'),
        )
        messages.success(request, 'Academic session added!')
        return redirect('academic_session_settings')
    
    return render(request, 'fees/add_academic_session.html')

# ============ FEE SETTINGS (Redirect) ============

@login_required
def fee_settings_dashboard(request):
    """Redirect to fee matrix"""
    return redirect('/fees/fee-matrix/')

# ============ SCHOLARSHIP MANAGEMENT ============

@login_required
def scholarship_management(request):
    scholarships = ScholarshipType.objects.filter(is_active=True).prefetch_related('applies_to_categories')
    return render(request, 'fees/scholarship_management.html', {'scholarships': scholarships})

@login_required
def add_scholarship(request):
    categories = FeeCategory.objects.filter(is_active=True)
    if request.method == 'POST':
        name = request.POST.get('name')
        category = request.POST.get('category')
        is_percentage = request.POST.get('is_percentage') == 'on'
        discount_value = request.POST.get('discount_value')
        applies_to_semester = request.POST.get('applies_to_semester', 'YEARLY')
        max_students = request.POST.get('max_students', 0)
        description = request.POST.get('description', '')
        
        scholarship = ScholarshipType.objects.create(
            name=name,
            category=category,
            is_percentage=is_percentage,
            discount_value=discount_value,
            applies_to_semester=applies_to_semester,
            max_students=max_students,
            description=description,
        )
        
        selected_categories = request.POST.getlist('applies_to_categories')
        if selected_categories:
            scholarship.applies_to_categories.set(selected_categories)
        
        messages.success(request, f'Scholarship "{name}" added successfully!')
        return redirect('scholarship_management')
    
    context = {'categories': categories}
    return render(request, 'fees/add_scholarship.html', context)

@login_required
def edit_scholarship(request, pk):
    scholarship = get_object_or_404(ScholarshipType, pk=pk)
    categories = FeeCategory.objects.filter(is_active=True)
    
    if request.method == 'POST':
        scholarship.name = request.POST.get('name')
        scholarship.category = request.POST.get('category')
        scholarship.is_percentage = request.POST.get('is_percentage') == 'on'
        scholarship.discount_value = request.POST.get('discount_value')
        scholarship.applies_to_semester = request.POST.get('applies_to_semester', 'YEARLY')
        scholarship.max_students = request.POST.get('max_students', 0)
        scholarship.description = request.POST.get('description', '')
        
        selected_categories = request.POST.getlist('applies_to_categories')
        scholarship.applies_to_categories.set(selected_categories)
        scholarship.save()
        
        messages.success(request, 'Scholarship updated successfully!')
        return redirect('scholarship_management')
    
    context = {
        'scholarship': scholarship,
        'categories': categories,
        'selected_categories': scholarship.applies_to_categories.all().values_list('id', flat=True),
    }
    return render(request, 'fees/edit_scholarship.html', context)

@login_required
def delete_scholarship(request, pk):
    scholarship = get_object_or_404(ScholarshipType, pk=pk)
    if request.method == 'POST':
        scholarship.is_active = False
        scholarship.save()
        messages.success(request, f'Scholarship "{scholarship.name}" deleted!')
        return redirect('scholarship_management')
    
    return render(request, 'fees/delete_scholarship.html', {'scholarship': scholarship})

@login_required
def assign_scholarship(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    available_scholarships = ScholarshipType.objects.filter(is_active=True)
    
    if request.method == 'POST':
        scholarship_id = request.POST.get('scholarship')
        academic_year = request.POST.get('academic_year', '2024')
        
        if scholarship_id:
            scholarship = get_object_or_404(ScholarshipType, id=scholarship_id)
            existing = StudentScholarship.objects.filter(
                student=student,
                scholarship=scholarship,
                academic_year=academic_year,
                is_active=True
            ).first()
            
            if existing:
                messages.warning(request, 'Student already has this scholarship')
            else:
                StudentScholarship.objects.create(
                    student=student,
                    scholarship=scholarship,
                    academic_year=academic_year,
                )
                messages.success(request, f'Scholarship "{scholarship.name}" assigned to {student.full_name}!')
        
        return redirect('student_detail', pk=student.id)
    
    student_scholarships = StudentScholarship.objects.filter(student=student, is_active=True).select_related('scholarship')
    
    context = {
        'student': student,
        'available_scholarships': available_scholarships,
        'student_scholarships': student_scholarships,
    }
    return render(request, 'fees/assign_scholarship.html', context)

@login_required
def check_installment_reminders(request):
    today = date.today()
    reminders = InstallmentReminder.objects.filter(is_paid=False, due_date__gte=today)[:20]
    overdue_count = InstallmentReminder.objects.filter(is_paid=False, due_date__lt=today).count()
    
    context = {
        'reminders': reminders,
        'total_overdue': overdue_count,
    }
    return render(request, 'fees/reminders.html', context)

@login_required
def auto_assign_fees_v2(request):
    if request.method == 'POST':
        academic_year = request.POST.get('academic_year', get_active_academic_year())
        students = Student.objects.filter(is_active=True)
        assigned_count = 0
        
        for student in students:
            if not student.class_assigned:
                continue
            
            fee_structures = FeeStructure.objects.filter(
                class_assigned=student.class_assigned,
                academic_year=academic_year,
                student_type=student.student_type,
                is_active=True
            )
            
            semester1_total_lrd = sum(f.semester1_amount_lrd for f in fee_structures)
            semester1_total_usd = sum(f.semester1_amount_usd for f in fee_structures)
            semester2_total_lrd = sum(f.semester2_amount_lrd for f in fee_structures)
            semester2_total_usd = sum(f.semester2_amount_usd for f in fee_structures)
            
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
            
            assigned_count += 1
        
        messages.success(request, f'Fees assigned to {assigned_count} students for {academic_year}')
        return redirect('fee_structure_matrix')
    
    academic_year = request.GET.get('academic_year', get_active_academic_year())
    context = {
        'academic_year': academic_year,
    }
    return render(request, 'fees/auto_assign_v2.html', context)
