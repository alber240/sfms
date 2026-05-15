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
    receipt_photo = models.ImageField(upload_to='expenses/%Y/%m/%d/', blank=True, null=True, 
                                       help_text='Upload photo of receipt or invoice')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.category.name} - {self.amount_lrd} LRD"
