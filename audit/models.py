from django.db import models
from django.contrib.auth.models import User

class AuditLog(models.Model):
    ACTION_TYPES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('VOID', 'Void'),
        ('UNDO', 'Undo'),
    ]
    
    TABLE_CHOICES = [
        ('receipts', 'Receipt'),
        ('expenses', 'Expense'),
        ('students', 'Student'),
        ('fees', 'Fee Structure'),
    ]
    
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    table_name = models.CharField(max_length=50)
    record_id = models.IntegerField()
    old_values = models.JSONField(null=True, blank=True)
    new_values = models.JSONField(null=True, blank=True)
    reason = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.action_type} - {self.table_name} #{self.record_id} - {self.created_at}"
    
    class Meta:
        ordering = ['-created_at']
