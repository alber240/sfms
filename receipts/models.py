from django.db import models
from django.db import transaction
from students.models import Student

class ReceiptSequence(models.Model):
    """Atomic receipt number generator - survives power loss"""
    id = models.IntegerField(primary_key=True, default=1)
    last_number = models.IntegerField(default=0)
    
    @classmethod
    def get_next_number(cls):
        with transaction.atomic():
            sequence = cls.objects.select_for_update().first()
            if not sequence:
                sequence = cls.objects.create(id=1, last_number=0)
            sequence.last_number += 1
            sequence.save()
            return sequence.last_number

class Receipt(models.Model):
    PAYMENT_METHODS = [
        ('CASH', 'Cash'),
        ('MOBILE_MONEY', 'Mobile Money'),
    ]
    
    receipt_number = models.IntegerField(unique=True, editable=False)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='receipts')
    payment_date = models.DateField(auto_now_add=True)
    amount_lrd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='CASH')
    mobile_transaction_id = models.CharField(max_length=100, blank=True)
    is_voided = models.BooleanField(default=False)
    void_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = ReceiptSequence.get_next_number()
        super().save(*args, **kwargs)
    
    @property
    def total_amount_lrd_equivalent(self):
        # For combined total (assuming 1 USD = 200 LRD for now)
        return self.amount_lrd + (self.amount_usd * 200)
    
    def __str__(self):
        return f"Receipt #{self.receipt_number} - {self.student.full_name}"
class BatchPaymentSession(models.Model):
    """Track batch payment sessions"""
    session_date = models.DateField(auto_now_add=True)
    created_by = models.CharField(max_length=50, default='accountant')
    total_receipts = models.IntegerField(default=0)
    total_amount_lrd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Batch {self.id} - {self.session_date} - {self.total_receipts} receipts"
