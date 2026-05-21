from django.db import models
from django.contrib.auth.models import User
from datetime import date

class Staff(models.Model):
    name = models.CharField(max_length=200)
    position = models.CharField(max_length=100)
    staff_id = models.CharField(max_length=20, unique=True)
    monthly_salary_lrd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    monthly_salary_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    hire_date = models.DateField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} - {self.position}"
    
    class Meta:
        ordering = ['name']

class StaffAdvance(models.Model):
    DEDUCTION_TYPES = [
        ('ADVANCE', 'Salary Advance'),
        ('LOAN', 'Loan Deduction'),
        ('COOPERATIVE', 'Cooperative Contribution'),
        ('PENALTY', 'Penalty'),
        ('ABSENCE', 'Absence Deduction'),
        ('OTHER', 'Other Deduction'),
    ]
    
    MONTH_CHOICES = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
    ]
    
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='advances')
    deduction_type = models.CharField(max_length=20, choices=DEDUCTION_TYPES, default='ADVANCE')
    month = models.IntegerField(choices=MONTH_CHOICES)
    year = models.IntegerField(default=date.today().year)
    amount_lrd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_applied = models.BooleanField(default=False, help_text="Whether this deduction has been applied to payroll")
    
    def __str__(self):
        return f"{self.staff.name} - {self.get_deduction_type_display()}: {self.amount_lrd} LRD ({self.get_month_display()} {self.year})"

class PayrollPeriod(models.Model):
    MONTH_CHOICES = [
        (1, 'January'), (2, 'February'), (3, 'March'), (4, 'April'),
        (5, 'May'), (6, 'June'), (7, 'July'), (8, 'August'),
        (9, 'September'), (10, 'October'), (11, 'November'), (12, 'December')
    ]
    
    month = models.IntegerField(choices=MONTH_CHOICES)
    year = models.IntegerField()
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    processed_at = models.DateTimeField(auto_now_add=True)
    total_amount_lrd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_processed = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['month', 'year']
        ordering = ['-year', '-month']
    
    def __str__(self):
        months = ['', 'January', 'February', 'March', 'April', 'May', 'June', 
                  'July', 'August', 'September', 'October', 'November', 'December']
        return f"{months[self.month]} {self.year}"

class PayrollEntry(models.Model):
    payroll_period = models.ForeignKey(PayrollPeriod, on_delete=models.CASCADE, related_name='entries')
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE)
    base_salary_lrd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    base_salary_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deduction_lrd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deduction_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    deduction_reason = models.TextField(blank=True)
    net_pay_lrd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    net_pay_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.staff.name} - {self.payroll_period}"
class PayrollReceipt(models.Model):
    payroll_entry = models.OneToOneField('PayrollEntry', on_delete=models.CASCADE, related_name='receipt')
    receipt_number = models.CharField(max_length=50, unique=True)
    printed_at = models.DateTimeField(auto_now_add=True)
    printed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        return f"Payroll Receipt #{self.receipt_number}"
class PayrollReceipt(models.Model):
    payroll_entry = models.OneToOneField('PayrollEntry', on_delete=models.CASCADE, related_name='receipt')
    receipt_number = models.CharField(max_length=50, unique=True)
    printed_at = models.DateTimeField(auto_now_add=True)
    printed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        return f"Payroll Receipt #{self.receipt_number}"

class StaffAttendance(models.Model):
    """Track staff attendance and performance"""
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='attendance')
    month = models.IntegerField()
    year = models.IntegerField()
    days_present = models.IntegerField(default=0)
    days_absent = models.IntegerField(default=0)
    days_late = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['staff', 'month', 'year']
    
    def __str__(self):
        return f"{self.staff.name} - {self.month}/{self.year} - Present: {self.days_present}"

class StaffPerformanceReview(models.Model):
    """Annual performance review for staff"""
    staff = models.ForeignKey(Staff, on_delete=models.CASCADE, related_name='reviews')
    review_date = models.DateField()
    academic_year = models.CharField(max_length=10)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], help_text="1=Poor, 5=Excellent")
    strengths = models.TextField(blank=True)
    areas_for_improvement = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    reviewed_by = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.staff.name} - {self.academic_year} - Rating: {self.rating}/5"

class StaffAttendance(models.Model):
    """Track staff attendance and performance"""
    staff = models.ForeignKey('Staff', on_delete=models.CASCADE, related_name='attendance')
    month = models.IntegerField()
    year = models.IntegerField()
    days_present = models.IntegerField(default=0)
    days_absent = models.IntegerField(default=0)
    days_late = models.IntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['staff', 'month', 'year']
    
    def __str__(self):
        return f"{self.staff.name} - {self.month}/{self.year} - Present: {self.days_present}"

class StaffPerformanceReview(models.Model):
    """Annual performance review for staff"""
    staff = models.ForeignKey('Staff', on_delete=models.CASCADE, related_name='reviews')
    review_date = models.DateField(auto_now_add=True)
    academic_year = models.CharField(max_length=10)
    rating = models.IntegerField(help_text="1=Poor, 5=Excellent")
    strengths = models.TextField(blank=True)
    areas_for_improvement = models.TextField(blank=True)
    recommendations = models.TextField(blank=True)
    reviewed_by = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.staff.name} - {self.academic_year} - Rating: {self.rating}/5"
