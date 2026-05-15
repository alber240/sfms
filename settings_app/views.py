from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from expenses.models import ExpenseCategory

@login_required
def settings_dashboard(request):
    """Main settings page"""
    categories = ExpenseCategory.objects.all()
    return render(request, 'settings_app/dashboard.html', {'categories': categories})

@login_required
def add_category(request):
    """Add expense category"""
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        
        if name and code:
            ExpenseCategory.objects.create(name=name, code=code)
            messages.success(request, f'Category "{name}" added successfully!')
        else:
            messages.error(request, 'Please provide both name and code')
        
        return redirect('settings_dashboard')
    
    return render(request, 'settings_app/add_category.html')

@login_required
def edit_category(request, pk):
    """Edit expense category"""
    category = get_object_or_404(ExpenseCategory, pk=pk)
    
    if request.method == 'POST':
        category.name = request.POST.get('name')
        category.code = request.POST.get('code')
        category.save()
        messages.success(request, 'Category updated!')
        return redirect('settings_dashboard')
    
    return render(request, 'settings_app/edit_category.html', {'category': category})

@login_required
def delete_category(request, pk):
    """Delete expense category"""
    category = get_object_or_404(ExpenseCategory, pk=pk)
    
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Category deleted!')
        return redirect('settings_dashboard')
    
    return render(request, 'settings_app/delete_category.html', {'category': category})

@login_required
def fee_settings(request):
    """Fee structure settings"""
    return render(request, 'settings_app/fee_settings.html')
