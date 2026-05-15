from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Expense, ExpenseCategory

@login_required
def expense_add(request):
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
            )
            
            # Handle photo upload
            if 'receipt_photo' in request.FILES:
                expense.receipt_photo = request.FILES['receipt_photo']
                expense.save()
                messages.success(request, 'Expense recorded with receipt photo!')
            else:
                messages.success(request, 'Expense recorded successfully!')
            
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
        # Delete the photo file if exists
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
