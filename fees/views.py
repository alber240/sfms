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

from .models import AcademicSession

def get_active_academic_year():
    """Get the currently active academic year"""
    active_session = AcademicSession.objects.filter(is_active=True).first()
    if active_session:
        return active_session.academic_year
    return '2025-2026'

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
    from .models import AcademicSession
    from students.models import Class
    from .models import FeeCategory, FeeStructure
    
    # Get class filter from request - define this FIRST
    class_filter = request.GET.get('class_filter')
    
    # Get all classes and categories
    all_classes = Class.objects.filter(is_active=True)
    categories = FeeCategory.objects.filter(is_active=True)
    
    # Apply filter if present
    if class_filter and class_filter.isdigit():
        classes = all_classes.filter(id=int(class_filter))
    else:
        classes = all_classes
        class_filter = None  # Reset if not valid
    
    # Check if user selected a specific year from the dropdown
    selected_year = request.GET.get('academic_year')
    
    if selected_year:
        request.session['selected_academic_year'] = selected_year
        academic_year = selected_year
    else:
        academic_year = request.session.get('selected_academic_year')
        if not academic_year:
            active_session = AcademicSession.objects.filter(is_active=True).first()
            academic_year = active_session.academic_year if active_session else '2025-2026'
    
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
    
    # Calculate class totals
    class_totals = {}
    for class_obj in classes:
        class_totals[class_obj.id] = {
            'sem1': {'lrd': 0, 'usd': 0},
            'sem2': {'lrd': 0, 'usd': 0}
        }
        for student_type in ['NEW', 'OLD']:
            for category in categories:
                fee_struct = FeeStructure.objects.filter(
                    class_assigned=class_obj,
                    academic_year=academic_year,
                    student_type=student_type,
                    category=category
                ).first()
                if fee_struct:
                    class_totals[class_obj.id]['sem1']['lrd'] += float(fee_struct.semester1_amount_lrd)
                    class_totals[class_obj.id]['sem1']['usd'] += float(fee_struct.semester1_amount_usd)
                    class_totals[class_obj.id]['sem2']['lrd'] += float(fee_struct.semester2_amount_lrd)
                    class_totals[class_obj.id]['sem2']['usd'] += float(fee_struct.semester2_amount_usd)
    
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
        redirect_url = f'/fees/fee-matrix/?academic_year={academic_year}'
        if class_filter:
            redirect_url += f'&class_filter={class_filter}'
        return redirect(redirect_url)
    
    available_years = ['2024-2025', '2025-2026', '2026-2027', '2027-2028']
    active_session = AcademicSession.objects.filter(is_active=True).first()
    active_year = active_session.academic_year if active_session else '2025-2026'
    
    context = {
        'classes': classes,
        'all_classes': all_classes,
        'categories': categories,
        'academic_year': academic_year,
        'student_types': ['NEW', 'OLD'],
        'fee_matrix': fee_matrix,
        'class_totals': class_totals,
        'available_years': available_years,
        'active_year': active_year,
        'class_filter': class_filter,
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
            applies_to_semester=applies_to_semester,  # ← ADD THIS - WAS MISSING!
            max_students=max_students,                # ← FIXED: changed from 'applies_to_max_students'
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

# In fees/views.py - update assign_scholarship function

@login_required
def assign_scholarship(request, student_id):
    from .models import ScholarshipType, StudentScholarship, StudentFeeLedger, FeeStructure
    from decimal import Decimal
    
    student = get_object_or_404(Student, pk=student_id)
    
    if request.method == 'POST':
        scholarship_id = request.POST.get('scholarship_id')
        academic_year = request.POST.get('academic_year', '2024')
        
        if not scholarship_id:
            messages.error(request, 'Please select a scholarship.')
            return redirect('assign_scholarship', student_id=student.id)
        
        scholarship = get_object_or_404(ScholarshipType, pk=scholarship_id)
        
        # Check if student already has this scholarship
        existing = StudentScholarship.objects.filter(
            student=student,
            scholarship=scholarship,
            academic_year=academic_year,
            is_active=True
        ).first()
        
        if existing:
            messages.warning(request, f'Student already has "{scholarship.name}" scholarship!')
            return redirect('student_detail', pk=student.id)
        
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
        
        # Get ALL fee structures
        all_fee_structures = FeeStructure.objects.filter(
            class_assigned=student.class_assigned,
            academic_year=academic_year,
            student_type=student.student_type,
            is_active=True
        )
        
        # Get the categories this scholarship applies to
        applies_to_categories = scholarship.applies_to_categories.all()
        category_ids = [cat.id for cat in applies_to_categories]
        
        # Calculate total fees for categories that receive the scholarship
        discount_total_lrd = Decimal('0')
        discount_total_usd = Decimal('0')
        
        # First, calculate discount only for selected categories
        if applies_to_categories:
            # Only apply to selected categories
            for fs in all_fee_structures:
                if fs.category.id in category_ids:
                    discount_total_lrd += fs.semester1_amount_lrd + fs.semester2_amount_lrd
                    discount_total_usd += fs.semester1_amount_usd + fs.semester2_amount_usd
        else:
            # Apply to ALL categories (no specific categories selected)
            for fs in all_fee_structures:
                discount_total_lrd += fs.semester1_amount_lrd + fs.semester2_amount_lrd
                discount_total_usd += fs.semester1_amount_usd + fs.semester2_amount_usd
        
        # Calculate the scholarship discount
        if scholarship.is_percentage:
            discount_lrd = discount_total_lrd * (Decimal(str(scholarship.discount_value)) / 100)
            discount_usd = discount_total_usd * (Decimal(str(scholarship.discount_value)) / 100)
        else:
            discount_lrd = Decimal(str(scholarship.discount_value))
            discount_usd = Decimal('0')
        
        # Set the discount in the ledger
        ledger.discount_applied_lrd = discount_lrd
        ledger.discount_applied_usd = discount_usd
        ledger.save()
        
        # Create the scholarship assignment
        student_scholarship = StudentScholarship.objects.create(
            student=student,
            scholarship=scholarship,
            academic_year=academic_year,
            is_active=True
        )
        
        # Show which categories received the discount
        if applies_to_categories:
            category_names = [cat.name for cat in applies_to_categories]
            category_text = ", ".join(category_names)
        else:
            category_text = "All Categories"
        
        messages.success(
            request,
            f'✅ Scholarship "{scholarship.name}" assigned to {student.full_name}! '
            f'Applied to: {category_text} | '
            f'LRD Discount: {discount_lrd:.0f} LRD | USD Discount: {discount_usd:.2f} USD'
        )
        return redirect('student_detail', pk=student.id)
    
    # GET request - show the form
    scholarships = ScholarshipType.objects.filter(is_active=True)
    existing_scholarships = StudentScholarship.objects.filter(
        student=student,
        is_active=True
    )
    
    context = {
        'student': student,
        'scholarships': scholarships,
        'existing_scholarships': existing_scholarships,
    }
    return render(request, 'fees/assign_scholarship.html', context)

    

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
    from .models import AcademicSession
    
    if request.method == 'POST':
        academic_year = request.POST.get('academic_year')
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
            
            assigned_count += 1
        
        messages.success(request, f'Fees assigned to {assigned_count} students for {academic_year}')
        return redirect(f'/fees/fee-matrix/?academic_year={academic_year}')
    
    # GET request - get year from session or URL
    academic_year = request.GET.get('academic_year') or request.session.get('selected_academic_year', '2025-2026')
    context = {
        'academic_year': academic_year,
    }
    return render(request, 'fees/auto_assign_v2.html', context)


@login_required
def manage_categories(request):
    """Manage fee categories - add, edit, delete"""
    categories = FeeCategory.objects.all().order_by('-is_active','code')
    return render(request, 'fees/manage_categories.html', {'categories': categories})

@login_required
def add_category(request):
    """Add new fee category"""
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code', '').upper().strip()
        
        if not name or not code:
            messages.error(request, 'Both name and code are required')
            return redirect('manage_categories')
        
        # Check if category already exists (including inactive)
        existing = FeeCategory.objects.filter(code=code).first()
        
        if existing:
            if existing.is_active:
                messages.error(request, f'Category with code "{code}" already exists!')
            else:
                # Reactivate inactive category
                existing.is_active = True
                existing.name = name
                existing.save()
                messages.success(request, f'Category "{name}" was inactive and has been reactivated!')
        else:
            # Create new category
            FeeCategory.objects.create(name=name, code=code, is_active=True)
            messages.success(request, f'Category "{name}" added successfully!')
        
        return redirect('manage_categories')
    
    return render(request, 'fees/add_category.html')
@login_required
def edit_category(request, pk):
    """Edit fee category"""
    category = get_object_or_404(FeeCategory, pk=pk)
    
    if request.method == 'POST':
        category.name = request.POST.get('name')
        category.code = request.POST.get('code')
        category.save()
        messages.success(request, 'Category updated successfully!')
        return redirect('manage_categories')
    
    return render(request, 'fees/edit_category.html', {'category': category})

@login_required
def delete_category(request, pk):
    """Delete fee category (soft delete - set inactive)"""
    category = get_object_or_404(FeeCategory, pk=pk)
    
    if request.method == 'POST':
        # Check if category is used in any fee structures
        used_in = FeeStructure.objects.filter(category=category).count()
        if used_in > 0:
            messages.warning(request, f'Cannot delete "{category.name}" because it is used in {used_in} fee structures. Set it as inactive instead.')
            return redirect('manage_categories')
        
        category.delete()
        messages.success(request, f'Category "{category.name}" deleted successfully!')
        return redirect('manage_categories')
    
    return render(request, 'fees/delete_category.html', {'category': category})

# Add to fees/views.py
@login_required
def inactive_categories(request):
    """View and reactivate inactive categories"""
    categories = FeeCategory.objects.filter(is_active=False).order_by('code')
    
    if request.method == 'POST':
        category_id = request.POST.get('category_id')
        action = request.POST.get('action')
        
        category = get_object_or_404(FeeCategory, pk=category_id)
        
        if action == 'reactivate':
            category.is_active = True
            category.save()
            messages.success(request, f'Category "{category.name}" has been reactivated!')
        elif action == 'delete':
            # Check if category is used
            used_in = FeeStructure.objects.filter(category=category).count()
            if used_in == 0:
                category.delete()
                messages.success(request, f'Category "{category.name}" deleted permanently!')
            else:
                messages.error(request, f'Cannot delete "{category.name}" - used in {used_in} fee structures.')
        
        return redirect('inactive_categories')
    
    context = {'categories': categories}
    return render(request, 'fees/inactive_categories.html', context)

@login_required
def toggle_category_status(request, pk):
    """Toggle category between active and inactive"""
    category = get_object_or_404(FeeCategory, pk=pk)
    
    if category.is_active:
        category.is_active = False
        messages.success(request, f'Category "{category.name}" has been deactivated.')
    else:
        category.is_active = True
        messages.success(request, f'Category "{category.name}" has been activated.')
    
    category.save()
    return redirect('manage_categories')