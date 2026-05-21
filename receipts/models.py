from datetime import date

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
    
    PAYMENT_PERIOD_CHOICES = [
        ('FIRST', '1st Semester'),
        ('SECOND', '2nd Semester'),
        ('YEARLY', 'Yearly (Both Semesters)'),
    ]
    
    receipt_number = models.IntegerField(unique=True, editable=False)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='receipts')
    payment_date = models.DateField(default=date.today)
    amount_lrd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='CASH')
    payment_period = models.CharField(max_length=10, choices=PAYMENT_PERIOD_CHOICES, default='FIRST')
    mobile_transaction_id = models.CharField(max_length=100, blank=True)
    is_voided = models.BooleanField(default=False)
    void_reason = models.TextField(blank=True)
    is_legacy = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        if not self.receipt_number:
            self.receipt_number = ReceiptSequence.get_next_number()
        super().save(*args, **kwargs)
    
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
    
class PaymentAllocation(models.Model):
    """Track which fee category each payment applies to"""
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE, related_name='allocations')
    fee_category = models.ForeignKey('fees.FeeCategory', on_delete=models.CASCADE)
    amount_lrd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.receipt.receipt_number} - {self.fee_category.name}: {self.amount_lrd} LRD"
