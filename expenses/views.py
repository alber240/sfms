from django.utils import timezone  # CHANGE THIS LINE

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Expense, ExpenseCategory

@login_required
def expense_add(request):
    from .models import ExpenseApproval
    
    categories = ExpenseCategory.objects.all()
    
    if request.method == 'POST':
        try:
            category_id = request.POST.get('category')
            amount_lrd = float(request.POST.get('amount_lrd', '0') or 0)
            amount_usd = float(request.POST.get('amount_usd', '0') or 0)
            
            if amount_lrd == 0 and amount_usd == 0:
                messages.error(request, 'Please enter an amount in LRD or USD')
                return redirect('expense_add')
            
            expense = Expense.objects.create(
                category_id=category_id,
                description=request.POST.get('description', ''),
                amount_lrd=amount_lrd,
                amount_usd=amount_usd,
                notes=request.POST.get('notes', ''),
                requested_by=request.user,
            )
            
            # Create approval record
            ExpenseApproval.objects.create(
                expense=expense,
                requested_by=request.user,
                status='PENDING'
            )
            
            # Handle photo upload
            if 'receipt_photo' in request.FILES:
                expense.receipt_photo = request.FILES['receipt_photo']
                expense.save()
                messages.success(request, 'Expense recorded with receipt photo! Pending approval.')
            else:
                messages.success(request, 'Expense recorded successfully! Pending approval.')
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
        
        return redirect('expense_list')
    
    context = {
        'categories': categories,
    }
    return render(request, 'expenses/add.html', context)

@login_required
def expense_list(request):
    expenses = Expense.objects.all().order_by('-expense_date')
    return render(request, 'expenses/list.html', {'expenses': expenses})

@login_required
def expense_delete(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    if request.method == 'POST':
        if expense.receipt_photo:
            expense.receipt_photo.delete()
        expense.delete()
        messages.success(request, 'Expense deleted!')
        return redirect('expense_list')
    return render(request, 'expenses/delete.html', {'expense': expense})

@login_required
def expense_view_photo(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    return render(request, 'expenses/view_photo.html', {'expense': expense})

@login_required
def expense_approval_list(request):
    """List expenses pending approval (for principal)"""
    from .models import ExpenseApproval
    
    if request.user.username != 'principal' and not request.user.username.startswith('pri_'):
        messages.error(request, 'Only principals can approve expenses')
        return redirect('expense_list')
    
    pending_approvals = ExpenseApproval.objects.filter(status='PENDING').select_related('expense', 'expense__category')
    approved_approvals = ExpenseApproval.objects.filter(status='APPROVED').select_related('expense', 'expense__category')[:20]
    rejected_approvals = ExpenseApproval.objects.filter(status='REJECTED').select_related('expense', 'expense__category')[:20]
    
    context = {
        'pending_approvals': pending_approvals,
        'approved_approvals': approved_approvals,
        'rejected_approvals': rejected_approvals,
        'pending_count': pending_approvals.count(),
    }
    return render(request, 'expenses/approval_list.html', context)

@login_required
def expense_approve(request, pk):
    """Approve an expense (principal only)"""
    from .models import ExpenseApproval
    
    if request.user.username != 'principal' and not request.user.username.startswith('pri_'):
        messages.error(request, 'Only principals can approve expenses')
        return redirect('expense_list')
    
    approval = get_object_or_404(ExpenseApproval, pk=pk)
    
    if request.method == 'POST':
        approval.status = 'APPROVED'
        approval.approved_by = request.user
        approval.approved_at = timezone.now()  # Now works correctly
        approval.approval_notes = request.POST.get('notes', '')
        approval.save()
        
        messages.success(request, f'Expense "{approval.expense.description}" approved successfully!')
        return redirect('expense_approval_list')
    
    return render(request, 'expenses/approve.html', {'approval': approval})

@login_required
def expense_reject(request, pk):
    """Reject an expense (principal only)"""
    from .models import ExpenseApproval
    
    if request.user.username != 'principal' and not request.user.username.startswith('pri_'):
        messages.error(request, 'Only principals can reject expenses')
        return redirect('expense_list')
    
    approval = get_object_or_404(ExpenseApproval, pk=pk)
    
    if request.method == 'POST':
        approval.status = 'REJECTED'
        approval.rejected_by = request.user
        approval.rejected_at = timezone.now()  # Now works correctly
        approval.rejection_reason = request.POST.get('reason', '')
        approval.save()
        
        messages.success(request, f'Expense "{approval.expense.description}" rejected.')
        return redirect('expense_approval_list')
    
    return render(request, 'expenses/reject.html', {'approval': approval})

@login_required
def expense_mark_paid(request, pk):
    """Mark approved expense as paid (accountant only)"""
    from .models import ExpenseApproval
    
    approval = get_object_or_404(ExpenseApproval, pk=pk)
    
    if request.method == 'POST':
        approval.status = 'PAID'
        approval.paid_by = request.user
        approval.paid_at = timezone.now()  # Now works correctly
        approval.payment_reference = request.POST.get('payment_reference', '')
        approval.save()
        
        messages.success(request, f'Expense "{approval.expense.description}" marked as paid.')
        return redirect('expense_list')
    
    return render(request, 'expenses/mark_paid.html', {'approval': approval})