from django.db import models
from students.models import Student, Class
from datetime import date

class FeeCategory(models.Model):
    name = models.CharField(max_length=100)
    name_fr = models.CharField(max_length=100, blank=True)
    code = models.CharField(max_length=20, unique=True)
    is_required = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.code})"
    
    class Meta:
        verbose_name_plural = "Fee Categories"

class AcademicSession(models.Model):
    SEMESTER_CHOICES = [
        ('FIRST', '1st Semester'),
        ('SECOND', '2nd Semester'),
    ]
    
    name = models.CharField(max_length=50)
    academic_year = models.CharField(max_length=10, unique=True)
    is_active = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)  # ← ADD THIS
    current_semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES, default='FIRST')
    start_date = models.DateField()
    end_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.academic_year} - {self.get_current_semester_display()}"
    
    class Meta:
        ordering = ['-academic_year']

class ScholarshipType(models.Model):
    SCHOLARSHIP_CATEGORIES = [
        ('ACADEMIC', 'Academic Excellence'),
        ('SPORTS', 'Sports'),
        ('NEED_BASED', 'Need Based'),
        ('MERIT', 'Merit'),
        ('SPECIAL', 'Special'),
    ]
    
    SEMESTER_CHOICES = [
        ('YEARLY', 'Yearly (Both Semesters)'),
        ('FIRST', '1st Semester Only'),
        ('SECOND', '2nd Semester Only'),
    ]
    
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=SCHOLARSHIP_CATEGORIES)
    description = models.TextField(blank=True)
    is_percentage = models.BooleanField(default=True)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2)
    applies_to_categories = models.ManyToManyField(FeeCategory, blank=True)
    applies_to_semester = models.CharField(max_length=20, choices=SEMESTER_CHOICES, default='YEARLY')
    max_students = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        discount_type = '%' if self.is_percentage else 'LRD'
        return f"{self.name} - {self.discount_value}{discount_type}"

class StudentScholarship(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='scholarships')
    scholarship = models.ForeignKey(ScholarshipType, on_delete=models.CASCADE)
    academic_year = models.CharField(max_length=10, default='2024')
    approved_date = models.DateField(auto_now_add=True)
    expiry_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.student.full_name} - {self.scholarship.name}"

class FeeStructure(models.Model):
    STUDENT_TYPE_CHOICES = [
        ('NEW', 'New Student'),
        ('OLD', 'Returning Student'),
    ]
    
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='fee_structures')
    academic_year = models.CharField(max_length=10, default='2024')
    student_type = models.CharField(max_length=10, choices=STUDENT_TYPE_CHOICES)
    category = models.ForeignKey(FeeCategory, on_delete=models.CASCADE)
    
    # Semester 1 amount
    semester1_amount_lrd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    semester1_amount_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Semester 2 amount
    semester2_amount_lrd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    semester2_amount_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['class_assigned', 'academic_year', 'student_type', 'category']
    
    @property
    def yearly_amount_lrd(self):
        return self.semester1_amount_lrd + self.semester2_amount_lrd
    
    @property
    def yearly_amount_usd(self):
        return self.semester1_amount_usd + self.semester2_amount_usd
    
    def __str__(self):
        return f"{self.class_assigned.name} - {self.get_student_type_display()} - {self.category.name}"

class InstallmentPlan(models.Model):
    SEMESTER_CHOICES = [
        ('FIRST', '1st Semester'),
        ('SECOND', '2nd Semester'),
    ]
    
    class_assigned = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='installments')
    academic_year = models.CharField(max_length=10, default='2024')
    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES)
    installment_number = models.IntegerField()
    due_date = models.DateField()
    percentage = models.DecimalField(max_digits=5, decimal_places=2)
    description = models.CharField(max_length=200, blank=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['due_date']
        unique_together = ['class_assigned', 'academic_year', 'semester', 'installment_number']
    
    def __str__(self):
        return f"{self.class_assigned.name} - {self.get_semester_display()} - Installment {self.installment_number}"

class StudentFeeLedger(models.Model):
    """Student fee ledger - tracks what each student owes and has paid"""
    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='fee_ledger')
    academic_year = models.CharField(max_length=10, default='2024')
    
    # Semester 1 totals and payments
    semester1_total_lrd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    semester1_total_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    semester1_paid_lrd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    semester1_paid_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Semester 2 totals and payments
    semester2_total_lrd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    semester2_total_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    semester2_paid_lrd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    semester2_paid_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Discounts applied
    discount_applied_lrd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    discount_applied_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Metadata
    last_payment_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def semester1_balance_lrd(self):
        return self.semester1_total_lrd - self.semester1_paid_lrd - (self.discount_applied_lrd / 2 if self.discount_applied_lrd else 0)
    
    @property
    def semester2_balance_lrd(self):
        return self.semester2_total_lrd - self.semester2_paid_lrd - (self.discount_applied_lrd / 2 if self.discount_applied_lrd else 0)
    
    @property
    def total_balance_lrd(self):
        return self.semester1_balance_lrd + self.semester2_balance_lrd
    
    @property
    def total_paid_lrd(self):
        return self.semester1_paid_lrd + self.semester2_paid_lrd
    
    @property
    def total_due_lrd(self):
        return self.semester1_total_lrd + self.semester2_total_lrd
    
    def __str__(self):
        return f"{self.student.full_name} - {self.academic_year} - Balance: {self.total_balance_lrd} LRD"

class InstallmentReminder(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    installment = models.ForeignKey(InstallmentPlan, on_delete=models.CASCADE)
    due_date = models.DateField()
    amount_due_lrd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_due_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_reminded = models.BooleanField(default=False)
    reminded_at = models.DateTimeField(null=True, blank=True)
    is_paid = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.student.full_name} - Due {self.due_date}"
