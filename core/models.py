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
class SchoolSetting(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.CharField(max_length=200, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.key}: {self.value[:50]}"
    
    class Meta:
        verbose_name_plural = "School Settings"

class EmailQueue(models.Model):
    """Queue emails when offline, send when internet available"""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('SENT', 'Sent'),
        ('FAILED', 'Failed'),
    ]
    
    to_email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    html_message = models.TextField(blank=True)
    attachment_path = models.CharField(max_length=500, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    attempts = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Email to {self.to_email} - {self.status}"
    
    class Meta:
        ordering = ['created_at']

from django.contrib.auth.models import User
from django.db.models.signals import post_save

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    require_password_change = models.BooleanField(default=True)
    school_code = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - Requires change: {self.require_password_change}"

# Signal to create user profile
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance, require_password_change=True)

post_save.connect(create_user_profile, sender=User)

from django.contrib.auth.models import User
from django.db.models.signals import post_save

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    require_password_change = models.BooleanField(default=True)
    school_code = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - Change required: {self.require_password_change}"

# Auto-create profile for new users
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance, require_password_change=True)

post_save.connect(create_user_profile, sender=User)
