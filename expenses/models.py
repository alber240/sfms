from django.db import models

class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    class Meta:
        verbose_name_plural = 'Expense Categories'

class Expense(models.Model):
    expense_date = models.DateField(auto_now_add=True)
    category = models.ForeignKey(ExpenseCategory, on_delete=models.CASCADE)
    description = models.TextField()
    amount_lrd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    receipt_photo = models.ImageField(upload_to='expenses/%Y/%m/%d/', blank=True, null=True)
    notes = models.TextField(blank=True)
    requested_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.category.name} - {self.amount_lrd} LRD"


class ExpenseApproval(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('PAID', 'Paid'),
    ]
    
    expense = models.OneToOneField(Expense, on_delete=models.CASCADE, related_name='approval')
    requested_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, related_name='requested_expenses')
    requested_at = models.DateTimeField(auto_now_add=True)
    
    approved_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_expenses')
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_notes = models.TextField(blank=True)
    
    rejected_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='rejected_expenses')
    rejected_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    paid_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='paid_expenses')
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    def __str__(self):
        return f"{self.expense.description} - {self.status}"
    
    class Meta:
        ordering = ['-requested_at']