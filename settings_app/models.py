from django.db import models
from expenses.models import ExpenseCategory

class SchoolSetting(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.CharField(max_length=200, blank=True)
    
    def __str__(self):
        return f"{self.key}: {self.value[:50]}"

class SystemSetting(models.Model):
    setting_name = models.CharField(max_length=100, unique=True)
    setting_value = models.TextField()
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.setting_name
