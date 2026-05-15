from django.db import models

# Create your models here.
class ExchangeRate(models.Model):
    rate_date = models.DateField(unique=True)
    lrd_to_usd = models.DecimalField(max_digits=10, decimal_places=4, help_text="1 USD = ? LRD")
    notes = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.rate_date}: 1 USD = {self.lrd_to_usd} LRD"
    
    class Meta:
        ordering = ['-rate_date']
        verbose_name = 'Exchange Rate'
        verbose_name_plural = 'Exchange Rates'
class DailyReminder(models.Model):
    reminder_date = models.DateField(unique=True)
    is_dismissed = models.BooleanField(default=False)
    dismissed_at = models.DateTimeField(null=True, blank=True)
    reminder_type = models.CharField(max_length=50, default='mobile_money')
    
    def __str__(self):
        return f"{self.reminder_date} - {'Dismissed' if self.is_dismissed else 'Pending'}"
    
    class Meta:
        ordering = ['-reminder_date']
