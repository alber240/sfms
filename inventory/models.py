from django.db import models

class InventoryCategory(models.Model):
    name = models.CharField(max_length=100)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Inventory Categories"

class InventoryItem(models.Model):
    name = models.CharField(max_length=200)
    category = models.ForeignKey(InventoryCategory, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.IntegerField(default=0)
    unit = models.CharField(max_length=20, default='piece')
    unit_price_lrd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit_price_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    low_stock_threshold = models.IntegerField(default=10)
    location = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit}s)"
    
    @property
    def is_low_stock(self):
        return self.quantity <= self.low_stock_threshold

class InventoryTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('IN', 'Stock In - Purchase'),
        ('OUT', 'Stock Out - Issued'),
        ('ADJUST', 'Adjustment'),
    ]
    
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    quantity = models.IntegerField()
    unit_price_lrd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit_price_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reference = models.CharField(max_length=100, blank=True)
    transaction_date = models.DateField(auto_now_add=True)
    notes = models.TextField(blank=True)
    created_by = models.CharField(max_length=50, default='accountant')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.item.name} x{self.quantity}"
