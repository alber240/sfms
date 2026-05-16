from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import InventoryItem, InventoryCategory

@login_required
def inventory_list(request):
    items = InventoryItem.objects.all()
    low_stock = [i for i in items if i.is_low_stock]
    return render(request, 'inventory/list.html', {'items': items, 'low_stock_count': len(low_stock)})

@login_required
def inventory_add(request):
    categories = InventoryCategory.objects.all()
    
    if request.method == 'POST':
        item = InventoryItem.objects.create(
            name=request.POST.get('name'),
            category_id=request.POST.get('category') or None,
            quantity=int(request.POST.get('quantity', 0)),
            unit=request.POST.get('unit', 'piece'),
            unit_price_lrd=request.POST.get('unit_price_lrd', 0),
            unit_price_usd=request.POST.get('unit_price_usd', 0),
            low_stock_threshold=request.POST.get('low_stock_threshold', 10),
            location=request.POST.get('location', ''),
            notes=request.POST.get('notes', ''),
        )
        messages.success(request, f'Added {item.name}')
        return redirect('inventory_list')
    
    return render(request, 'inventory/add.html', {'categories': categories})

@login_required
def inventory_edit(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    categories = InventoryCategory.objects.all()
    
    if request.method == 'POST':
        item.name = request.POST.get('name')
        item.category_id = request.POST.get('category') or None
        item.quantity = int(request.POST.get('quantity', 0))
        item.unit = request.POST.get('unit', 'piece')
        item.unit_price_lrd = request.POST.get('unit_price_lrd', 0)
        item.unit_price_usd = request.POST.get('unit_price_usd', 0)
        item.low_stock_threshold = request.POST.get('low_stock_threshold', 10)
        item.location = request.POST.get('location', '')
        item.notes = request.POST.get('notes', '')
        item.save()
        messages.success(request, 'Item updated!')
        return redirect('inventory_list')
    
    return render(request, 'inventory/edit.html', {'item': item, 'categories': categories})

@login_required
def inventory_delete(request, pk):
    item = get_object_or_404(InventoryItem, pk=pk)
    if request.method == 'POST':
        item.delete()
        messages.success(request, 'Item deleted!')
        return redirect('inventory_list')
    return render(request, 'inventory/delete.html', {'item': item})

@login_required
def inventory_category_add(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            InventoryCategory.objects.create(name=name)
            messages.success(request, f'Category "{name}" added!')
    return redirect('inventory_list')


@login_required
def inventory_category_list(request):
    """List all inventory categories"""
    categories = InventoryCategory.objects.all()
    return render(request, 'inventory/category_list.html', {'categories': categories})

@login_required
def inventory_category_add(request):
    """Add new inventory category"""
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            InventoryCategory.objects.create(name=name)
            messages.success(request, f'Category "{name}" added successfully!')
        else:
            messages.error(request, 'Category name is required')
        return redirect('inventory_category_list')
    
    return render(request, 'inventory/category_add.html')

@login_required
def inventory_category_edit(request, pk):
    """Edit inventory category"""
    category = get_object_or_404(InventoryCategory, pk=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            category.name = name
            category.save()
            messages.success(request, 'Category updated successfully!')
        else:
            messages.error(request, 'Category name is required')
        return redirect('inventory_category_list')
    
    return render(request, 'inventory/category_edit.html', {'category': category})

@login_required
def inventory_category_delete(request, pk):
    """Delete inventory category"""
    category = get_object_or_404(InventoryCategory, pk=pk)
    
    if request.method == 'POST':
        # Check if category has items
        if category.inventoryitem_set.count() > 0:
            messages.error(request, f'Cannot delete "{category.name}" because it has items assigned to it.')
            return redirect('inventory_category_list')
        
        category.delete()
        messages.success(request, 'Category deleted successfully!')
        return redirect('inventory_category_list')
    
    return render(request, 'inventory/category_delete.html', {'category': category})


@login_required
def inventory_issue(request, pk):
    """Issue/withdraw inventory items"""
    item = get_object_or_404(InventoryItem, pk=pk)
    
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 0))
        reference = request.POST.get('reference', '')
        notes = request.POST.get('notes', '')
        
        if quantity <= 0:
            messages.error(request, 'Quantity must be greater than 0')
            return redirect('inventory_issue', pk=pk)
        
        if quantity > item.quantity:
            messages.error(request, f'Not enough stock! Available: {item.quantity}')
            return redirect('inventory_issue', pk=pk)
        
        # Update stock
        item.quantity -= quantity
        item.save()
        
        # Create transaction record
        from .models import InventoryTransaction
        InventoryTransaction.objects.create(
            item=item,
            transaction_type='OUT',
            quantity=quantity,
            reference=reference,
            notes=notes,
            created_by=request.user.username
        )
        
        messages.success(request, f'Issued {quantity} {item.unit}(s) of {item.name}')
        return redirect('inventory_list')
    
    return render(request, 'inventory/issue.html', {'item': item})


@login_required
def inventory_category_list(request):
    """List all inventory categories"""
    from .models import InventoryCategory
    categories = InventoryCategory.objects.all()
    return render(request, 'inventory/category_list.html', {'categories': categories})


@login_required
def inventory_category_add(request):
    """Add new inventory category"""
    from .models import InventoryCategory
    
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            InventoryCategory.objects.create(name=name)
            messages.success(request, f'Category "{name}" added successfully!')
        else:
            messages.error(request, 'Category name is required')
        return redirect('inventory_category_list')
    
    return render(request, 'inventory/category_add.html')


@login_required
def inventory_category_edit(request, pk):
    """Edit inventory category"""
    from .models import InventoryCategory
    category = get_object_or_404(InventoryCategory, pk=pk)
    
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            category.name = name
            category.save()
            messages.success(request, 'Category updated successfully!')
        else:
            messages.error(request, 'Category name is required')
        return redirect('inventory_category_list')
    
    return render(request, 'inventory/category_edit.html', {'category': category})


@login_required
def inventory_category_delete(request, pk):
    """Delete inventory category"""
    from .models import InventoryCategory
    category = get_object_or_404(InventoryCategory, pk=pk)
    
    if request.method == 'POST':
        # Check if category has items
        if category.inventoryitem_set.count() > 0:
            messages.error(request, f'Cannot delete "{category.name}" because it has items assigned to it.')
            return redirect('inventory_category_list')
        
        category.delete()
        messages.success(request, 'Category deleted successfully!')
        return redirect('inventory_category_list')
    
    return render(request, 'inventory/category_delete.html', {'category': category})
