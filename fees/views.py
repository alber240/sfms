from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.db.models import Q, Sum
from datetime import date, datetime, timedelta
from decimal import Decimal
import re

from students.models import Student, Class, StudentYearStatus
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


# ============================================================
# HELPER FUNCTIONS
# ============================================================

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


# ============================================================
# FEE STRUCTURE MATRIX
# ============================================================

@login_required
def fee_structure_matrix(request):
    """Matrix view for setting fees with Yearly, Sem1, Sem2 per category"""
    class_filter = request.GET.get('class_filter')
    
    all_classes = Class.objects.filter(is_active=True)
    categories = FeeCategory.objects.filter(is_active=True)
    
    if class_filter and class_filter.isdigit():
        classes = all_classes.filter(id=int(class_filter))
    else:
        classes = all_classes
        class_filter = None
    
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


# ============================================================
# INSTALLMENT PLANS
# ============================================================

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


# ============================================================
# ACADEMIC SESSIONS
# ============================================================

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


# ============================================================
# FEE SETTINGS DASHBOARD
# ============================================================

@login_required
def fee_settings_dashboard(request):
    """Redirect to fee matrix"""
    return redirect('/fees/fee-matrix/')


# ============================================================
# SCHOLARSHIP MANAGEMENT
# ============================================================

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
    student = get_object_or_404(Student, pk=student_id)
    
    if request.method == 'POST':
        scholarship_id = request.POST.get('scholarship_id')
        academic_year = request.POST.get('academic_year', '2024')
        
        if not scholarship_id:
            messages.error(request, 'Please select a scholarship.')
            return redirect('assign_scholarship', student_id=student.id)
        
        scholarship = get_object_or_404(ScholarshipType, pk=scholarship_id)
        
        existing = StudentScholarship.objects.filter(
            student=student,
            scholarship=scholarship,
            academic_year=academic_year,
            is_active=True
        ).first()
        
        if existing:
            messages.warning(request, f'Student already has "{scholarship.name}" scholarship!')
            return redirect('student_detail', pk=student.id)
        
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
        
        all_fee_structures = FeeStructure.objects.filter(
            class_assigned=student.class_assigned,
            academic_year=academic_year,
            student_type=student.student_type,
            is_active=True
        )
        
        applies_to_categories = scholarship.applies_to_categories.all()
        category_ids = [cat.id for cat in applies_to_categories]
        
        discount_total_lrd = Decimal('0')
        discount_total_usd = Decimal('0')
        
        if applies_to_categories:
            for fs in all_fee_structures:
                if fs.category.id in category_ids:
                    discount_total_lrd += fs.semester1_amount_lrd + fs.semester2_amount_lrd
                    discount_total_usd += fs.semester1_amount_usd + fs.semester2_amount_usd
        else:
            for fs in all_fee_structures:
                discount_total_lrd += fs.semester1_amount_lrd + fs.semester2_amount_lrd
                discount_total_usd += fs.semester1_amount_usd + fs.semester2_amount_usd
        
        if scholarship.is_percentage:
            discount_lrd = discount_total_lrd * (Decimal(str(scholarship.discount_value)) / 100)
            discount_usd = discount_total_usd * (Decimal(str(scholarship.discount_value)) / 100)
        else:
            discount_lrd = Decimal(str(scholarship.discount_value))
            discount_usd = Decimal('0')
        
        ledger.discount_applied_lrd = discount_lrd
        ledger.discount_applied_usd = discount_usd
        ledger.save()
        
        StudentScholarship.objects.create(
            student=student,
            scholarship=scholarship,
            academic_year=academic_year,
            is_active=True
        )
        
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


# ============================================================
# INSTALLMENT REMINDERS
# ============================================================

def check_installment_reminders(request):
    today = date.today()
    reminders = InstallmentReminder.objects.filter(is_paid=False, due_date__gte=today)[:20]
    overdue_count = InstallmentReminder.objects.filter(is_paid=False, due_date__lt=today).count()
    
    context = {
        'reminders': reminders,
        'total_overdue': overdue_count,
    }
    return render(request, 'fees/reminders.html', context)


# ============================================================
# AUTO ASSIGN FEES
# ============================================================

@login_required
def auto_assign_fees_v2(request):
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
    
    academic_year = request.GET.get('academic_year') or request.session.get('selected_academic_year', '2025-2026')
    context = {
        'academic_year': academic_year,
    }
    return render(request, 'fees/auto_assign_v2.html', context)


# ============================================================
# FEE CATEGORY MANAGEMENT
# ============================================================

@login_required
def manage_categories(request):
    """Manage fee categories - add, edit, delete"""
    categories = FeeCategory.objects.all().order_by('-is_active', 'code')
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
        
        existing = FeeCategory.objects.filter(code=code).first()
        
        if existing:
            if existing.is_active:
                messages.error(request, f'Category with code "{code}" already exists!')
            else:
                existing.is_active = True
                existing.name = name
                existing.save()
                messages.success(request, f'Category "{name}" was inactive and has been reactivated!')
        else:
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
        used_in = FeeStructure.objects.filter(category=category).count()
        if used_in > 0:
            messages.warning(request, f'Cannot delete "{category.name}" because it is used in {used_in} fee structures. Set it as inactive instead.')
            return redirect('manage_categories')
        
        category.delete()
        messages.success(request, f'Category "{category.name}" deleted successfully!')
        return redirect('manage_categories')
    
    return render(request, 'fees/delete_category.html', {'category': category})


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


# ============================================================
# ACADEMIC YEAR MANAGEMENT
# ============================================================

@login_required
def start_new_academic_year(request):
    """Start a new academic year - reset everything except students and staff"""
    from expenses.models import Expense, ExpenseCategory
    from receipts.models import Receipt, PaymentAllocation
    from payroll.models import PayrollEntry, PayrollReceipt
    
    if request.method == 'POST':
        new_year = request.POST.get('academic_year')
        new_semester = request.POST.get('current_semester', 'FIRST')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        
        if not new_year:
            messages.error(request, 'Please enter academic year.')
            return redirect('start_academic_year')
        
        if AcademicSession.objects.filter(academic_year=new_year).exists():
            messages.error(request, f'Academic year {new_year} already exists.')
            return redirect('start_academic_year')
        
        try:
            with transaction.atomic():
                current_active = AcademicSession.objects.filter(is_active=True).first()
                if current_active:
                    current_active.is_active = False
                    current_active.is_archived = True
                    current_active.save()
                
                new_session = AcademicSession.objects.create(
                    name=f"{new_year} Academic Year",
                    academic_year=new_year,
                    is_active=True,
                    is_archived=False,
                    current_semester=new_semester,
                    start_date=start_date or datetime.now().date(),
                    end_date=end_date or datetime.now().date() + timedelta(days=365)
                )
                
                # Reset data
                StudentFeeLedger.objects.filter(academic_year=new_year).delete()
                FeeStructure.objects.filter(academic_year=new_year).delete()
                StudentScholarship.objects.filter(academic_year=new_year).delete()
                PayrollEntry.objects.all().delete()
                PayrollReceipt.objects.all().delete()
                Expense.objects.all().delete()
                Receipt.objects.all().delete()
                PaymentAllocation.objects.all().delete()
                
                for student in Student.objects.filter(is_active=True):
                    StudentFeeLedger.objects.create(
                        student=student,
                        academic_year=new_year,
                        semester1_total_lrd=Decimal('0'),
                        semester1_total_usd=Decimal('0'),
                        semester2_total_lrd=Decimal('0'),
                        semester2_total_usd=Decimal('0'),
                        semester1_paid_lrd=Decimal('0'),
                        semester1_paid_usd=Decimal('0'),
                        semester2_paid_lrd=Decimal('0'),
                        semester2_paid_usd=Decimal('0'),
                        discount_applied_lrd=Decimal('0'),
                        discount_applied_usd=Decimal('0')
                    )
                
                messages.success(
                    request, 
                    f'✅ Academic year {new_year} started successfully!'
                )
                return redirect('dashboard')
                
        except Exception as e:
            messages.error(request, f'Error starting academic year: {str(e)}')
            return redirect('start_academic_year')
    
    current_year = AcademicSession.objects.filter(is_active=True).first()
    
    current_year_num = datetime.now().year
    available_years = []
    
    for i in range(5, 0, -1):
        year = f"{current_year_num - i}-{current_year_num - i + 1}"
        available_years.append(year)
    
    for i in range(10):
        year = f"{current_year_num + i}-{current_year_num + i + 1}"
        available_years.append(year)
    
    context = {
        'current_year': current_year,
        'available_years': available_years,
        'today': datetime.now().date(),
        'end_date': datetime.now().date() + timedelta(days=365),
    }
    return render(request, 'fees/start_academic_year.html', context)


@login_required
def view_academic_year(request, year=None):
    """View data for a specific academic year"""
    from receipts.models import Receipt
    from expenses.models import Expense
    from students.models import Student, StudentYearStatus
    
    # ============================================================
    # FIX: Read year from URL parameter OR GET parameter
    # ============================================================
    if not year:
        year = request.GET.get('year')
    
    all_years = AcademicSession.objects.all().order_by('-academic_year')
    
    if not year:
        current = AcademicSession.objects.filter(is_active=True).first()
        if current:
            year = current.academic_year
        else:
            year = all_years.first().academic_year if all_years else None
    
    academic_session = AcademicSession.objects.filter(academic_year=year).first()
    
    if not academic_session:
        messages.error(request, f'Academic year {year} not found.')
        return redirect('dashboard')
    
    is_current = academic_session.is_active
    is_archived = academic_session.is_archived
    
    # Filter by academic_year
    receipts = Receipt.objects.filter(
        academic_year=year,
        is_voided=False
    ).order_by('-payment_date')
    
    expenses = Expense.objects.filter(
        academic_year=year
    ).order_by('-expense_date')
    
    # Students active in this year
    student_statuses = StudentYearStatus.objects.filter(academic_year=year)
    active_student_ids = student_statuses.exclude(
        status__in=['LEAVE', 'DROPOUT', 'GRADUATED']
    ).values_list('student_id', flat=True)
    
    if is_current:
        students = Student.objects.filter(is_active=True)
    else:
        students = Student.objects.filter(id__in=active_student_ids)
    
    fee_structures = FeeStructure.objects.filter(academic_year=year)
    ledgers = StudentFeeLedger.objects.filter(academic_year=year)
    
    total_collected_lrd = receipts.aggregate(Sum('amount_lrd'))['amount_lrd__sum'] or 0
    total_collected_usd = receipts.aggregate(Sum('amount_usd'))['amount_usd__sum'] or 0
    total_expenses_lrd = expenses.aggregate(Sum('amount_lrd'))['amount_lrd__sum'] or 0
    total_expenses_usd = expenses.aggregate(Sum('amount_usd'))['amount_usd__sum'] or 0
    
    net_cash = float(total_collected_lrd) - float(total_expenses_lrd)
    net_cash_usd = float(total_collected_usd) - float(total_expenses_usd)
    
    context = {
        'academic_session': academic_session,
        'all_years': all_years,
        'selected_year': year,
        'is_current': is_current,
        'is_archived': is_archived,
        'receipts': receipts[:20],
        'expenses': expenses[:20],
        'fee_structures': fee_structures,
        'ledgers': ledgers,
        'total_collected_lrd': total_collected_lrd,
        'total_collected_usd': total_collected_usd,
        'total_expenses_lrd': total_expenses_lrd,
        'total_expenses_usd': total_expenses_usd,
        'student_count': students.count(),
        'receipt_count': receipts.count(),
        'expense_count': expenses.count(),
        'net_cash': net_cash,
        'net_cash_usd': net_cash_usd,
    }
    return render(request, 'fees/view_academic_year.html', context)


# ============================================================
# YEAR TRANSITION WIZARD
# ============================================================

@login_required
def year_transition(request):
    """Step 1: Enter new year details"""
    current_year = AcademicSession.objects.filter(is_active=True).first()
    
    if not current_year:
        messages.error(request, 'No active academic year found. Please create one first.')
        return redirect('start_academic_year')
    
    if request.method == 'POST':
        request.session['transition_year'] = request.POST.get('academic_year')
        request.session['transition_semester'] = request.POST.get('current_semester', 'FIRST')
        request.session['transition_start'] = request.POST.get('start_date')
        request.session['transition_end'] = request.POST.get('end_date')
        request.session.modified = True
        return redirect('year_transition_step2')
    
    available_years = []
    try:
        parts = current_year.academic_year.replace('-', '/').split('/')
        if len(parts) == 2:
            for i in range(1, 5):
                next_year = f"{int(parts[0]) + i}/{int(parts[1]) + i}"
                available_years.append(next_year)
    except:
        pass
    
    context = {
        'current_year': current_year,
        'available_years': available_years,
        'today': datetime.now().date(),
        'end_date': datetime.now().date() + timedelta(days=365),
    }
    return render(request, 'fees/year_transition_step1.html', context)


@login_required
def year_transition_step2(request):
    """Step 2: Review students and set statuses"""
    current_year = AcademicSession.objects.filter(is_active=True).first()
    new_year = request.session.get('transition_year')
    
    if not current_year or not new_year:
        messages.error(request, 'Session expired. Please start again.')
        return redirect('year_transition')
    
    students = Student.objects.filter(is_active=True).order_by('class_assigned__name', 'last_name')
    classes = Class.objects.filter(is_active=True).order_by('name')
    
    student_data = []
    for student in students:
        current_class = student.class_assigned
        suggested_class = None
        is_final_grade = False
        
        if current_class:
            match = re.search(r'(\d+)', current_class.name)
            if match:
                current_grade = int(match.group(1))
                if current_grade >= 12:
                    is_final_grade = True
                else:
                    next_grade = current_grade + 1
                    suggested_class = Class.objects.filter(
                        name__icontains=str(next_grade),
                        is_active=True
                    ).first()
        
        student_data.append({
            'student': student,
            'suggested_status': 'GRADUATED' if is_final_grade else 'PROMOTED',
            'suggested_class': suggested_class.id if suggested_class else (current_class.id if current_class else None),
            'is_final_grade': is_final_grade,
        })
    
    if request.method == 'POST':
        # Save statuses to session
        statuses = {'class_data': {}}
        for key, value in request.POST.items():
            if key.startswith('status_'):
                student_id = key.replace('status_', '')
                statuses[f'status_{student_id}'] = value
            if key.startswith('class_'):
                student_id = key.replace('class_', '')
                statuses['class_data'][student_id] = value
        
        request.session['transition_statuses'] = statuses
        request.session.modified = True
        
        # Debug: print to console
        print(f"Saved statuses: {statuses}")
        
        return redirect('year_transition_step3')
    
    context = {
        'current_year': current_year,
        'new_year': new_year,
        'student_data': student_data,
        'classes': classes,
    }
    return render(request, 'fees/year_transition_step2.html', context)


@login_required
def year_transition_step3(request):
    """Step 3: Confirm and apply changes"""
    current_year = AcademicSession.objects.filter(is_active=True).first()
    new_year = request.session.get('transition_year')
    new_semester = request.session.get('transition_semester', 'FIRST')
    start_date = request.session.get('transition_start')
    end_date = request.session.get('transition_end')
    statuses = request.session.get('transition_statuses', {})
    
    if not current_year or not new_year:
        messages.error(request, 'Session expired. Please start again.')
        return redirect('year_transition')
    
    # On POST, collect statuses from form if session is empty
    if request.method == 'POST':
        # Try to get from session first
        if not statuses:
            # Collect from POST form
            statuses = {'class_data': {}}
            for key, value in request.POST.items():
                if key.startswith('status_'):
                    student_id = key.replace('status_', '')
                    statuses[f'status_{student_id}'] = value
                if key.startswith('class_'):
                    student_id = key.replace('class_', '')
                    statuses['class_data'][student_id] = value
            request.session['transition_statuses'] = statuses
            request.session.modified = True
        
        if not statuses:
            messages.error(request, 'No student statuses found. Please start again.')
            return redirect('year_transition_step2')
        
        try:
            with transaction.atomic():
                # ============================================================
                # 1. Archive current year
                # ============================================================
                current_year.is_active = False
                current_year.is_archived = True
                current_year.save()
                
                # ============================================================
                # 2. Create new academic year
                # ============================================================
                new_session = AcademicSession.objects.create(
                    name=f"{new_year} Academic Year",
                    academic_year=new_year,
                    is_active=True,
                    is_archived=False,
                    current_semester=new_semester,
                    start_date=start_date or datetime.now().date(),
                    end_date=end_date or datetime.now().date() + timedelta(days=365),
                    previous_year=current_year.academic_year
                )
                
                # ============================================================
                # 3. Copy fee structures
                # ============================================================
                old_fee_structures = FeeStructure.objects.filter(academic_year=current_year.academic_year)
                for fs in old_fee_structures:
                    FeeStructure.objects.create(
                        class_assigned=fs.class_assigned,
                        academic_year=new_year,
                        student_type=fs.student_type,
                        category=fs.category,
                        semester1_amount_lrd=fs.semester1_amount_lrd,
                        semester1_amount_usd=fs.semester1_amount_usd,
                        semester2_amount_lrd=fs.semester2_amount_lrd,
                        semester2_amount_usd=fs.semester2_amount_usd,
                        is_active=True
                    )
                
                # ============================================================
                # 4. Process each student
                # ============================================================
                students = Student.objects.filter(is_active=True)
                class_data = statuses.get('class_data', {})
                
                for student in students:
                    status = statuses.get(f'status_{student.id}', 'PROMOTED')
                    
                    # Check final grade (Grade 12)
                    current_class = student.class_assigned
                    is_final_grade = False
                    if current_class:
                        match = re.search(r'(\d+)', current_class.name)
                        if match:
                            current_grade = int(match.group(1))
                            if current_grade >= 12:
                                is_final_grade = True
                    
                    # Final grade students can only Graduate or Dropout
                    if is_final_grade:
                        if status not in ['GRADUATED', 'DROPOUT']:
                            status = 'GRADUATED'
                    
                    new_class = student.class_assigned
                    if str(student.id) in class_data:
                        try:
                            new_class = Class.objects.get(id=class_data[str(student.id)])
                        except Class.DoesNotExist:
                            pass
                    
                    # Create year status record
                    StudentYearStatus.objects.create(
                        student=student,
                        academic_year=new_year,
                        previous_class=student.class_assigned,
                        new_class=new_class if status in ['PROMOTED', 'REPEAT', 'DEMOTED'] else None,
                        status=status,
                        previous_type=student.student_type,
                        new_type='OLD' if status in ['PROMOTED', 'REPEAT', 'DEMOTED'] else student.student_type,
                    )
                    
                    # Update student record
                    if status in ['PROMOTED', 'REPEAT', 'DEMOTED']:
                        student.class_assigned = new_class
                        student.student_type = 'OLD'
                        student.is_active = True
                        student.save()
                    elif status in ['GRADUATED', 'LEAVE', 'DROPOUT']:
                        student.is_active = False
                        if status == 'GRADUATED':
                            student.left_school_date = datetime.now().date()
                        elif status == 'LEAVE':
                            student.left_school_date = datetime.now().date()
                        elif status == 'DROPOUT':
                            student.dropout_date = datetime.now().date()
                        student.archive_date = datetime.now().date() + timedelta(days=365)
                        student.save()
                
                # ============================================================
                # 5. Create new ledgers for active students
                # ============================================================
                for student in Student.objects.filter(is_active=True):
                    fee_structures = FeeStructure.objects.filter(
                        class_assigned=student.class_assigned,
                        academic_year=new_year,
                        student_type=student.student_type,
                        is_active=True
                    )
                    
                    total_lrd = Decimal('0')
                    total_usd = Decimal('0')
                    
                    for fs in fee_structures:
                        total_lrd += fs.semester1_amount_lrd + fs.semester2_amount_lrd
                        total_usd += fs.semester1_amount_usd + fs.semester2_amount_usd
                    
                    StudentFeeLedger.objects.create(
                        student=student,
                        academic_year=new_year,
                        semester1_total_lrd=total_lrd / 2 if total_lrd > 0 else 0,
                        semester1_total_usd=total_usd / 2 if total_usd > 0 else 0,
                        semester2_total_lrd=total_lrd / 2 if total_lrd > 0 else 0,
                        semester2_total_usd=total_usd / 2 if total_usd > 0 else 0,
                        semester1_paid_lrd=Decimal('0'),
                        semester1_paid_usd=Decimal('0'),
                        semester2_paid_lrd=Decimal('0'),
                        semester2_paid_usd=Decimal('0'),
                        discount_applied_lrd=Decimal('0'),
                        discount_applied_usd=Decimal('0')
                    )
                
                # ============================================================
                # 6. Clear session
                # ============================================================
                for key in ['transition_year', 'transition_semester', 'transition_start', 'transition_end', 'transition_statuses']:
                    if key in request.session:
                        del request.session[key]
                request.session.modified = True
                
                # ============================================================
                # 7. Run auto-archive for old years
                # ============================================================
                try:
                    from core.archive_utils import run_auto_archive
                    archive_results = run_auto_archive()
                    archived_count = sum(1 for r in archive_results if r['success'])
                    if archived_count > 0:
                        messages.info(request, f'📦 {archived_count} old year(s) automatically archived.')
                except Exception as e:
                    # Don't block transition if archive fails
                    print(f"Archive error: {str(e)}")
                    pass
                
                # ============================================================
                # 8. Success message
                # ============================================================
                messages.success(request, f'✅ Successfully transitioned to {new_year}!')
                return redirect('dashboard')
                
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('year_transition_step3')
    
    # GET request - show confirmation
    status_count = len([k for k in statuses.keys() if k.startswith('status_')])
    student_count = Student.objects.filter(is_active=True).count()
    
    context = {
        'current_year': current_year,
        'new_year': new_year,
        'student_count': student_count,
        'status_count': status_count,
        'statuses': statuses,
    }
    return render(request, 'fees/year_transition_step3.html', context)