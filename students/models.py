from django.db import models
from django.utils import timezone

class Class(models.Model):
    name = models.CharField(max_length=50)  # Removed unique=True
    section = models.CharField(max_length=10, blank=True)
    promotion_target = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        if self.section:
            return f"{self.name} - {self.section}"
        return self.name
    
    class Meta:
        verbose_name_plural = "Classes"
        ordering = ['name', 'section']
        unique_together = ['name', 'section']  # Allow same name with different sections

class Student(models.Model):
    STUDENT_TYPE_CHOICES = [
        ('NEW', 'New Student'),
        ('OLD', 'Returning Student'),
    ]
    
    admission_number = models.CharField(max_length=20, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    class_assigned = models.ForeignKey(Class, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    student_type = models.CharField(max_length=10, choices=STUDENT_TYPE_CHOICES, default='NEW')
    parent_name = models.CharField(max_length=200, blank=True)
    parent_phone = models.CharField(max_length=20, blank=True)
    parent_phone_alternative = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    student_photo = models.ImageField(upload_to='student_photos/', blank=True, null=True)
    enrollment_date = models.DateField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    graduated = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def get_class_name(self):
        return str(self.class_assigned) if self.class_assigned else "Not Assigned"
    
    def __str__(self):
        return f"{self.admission_number} - {self.full_name} ({self.get_student_type_display()})"
    
    class Meta:
        ordering = ['last_name', 'first_name']

class StudentYearStatus(models.Model):
    """Track student status for each academic year"""
    
    STATUS_CHOICES = [
        ('PROMOTED', 'Promoted'),
        ('REPEAT', 'Repeating'),
        ('DEMOTED', 'Demoted'),
        ('GRADUATED', 'Graduated'),
        ('LEAVE', 'Left School'),
        ('DROPOUT', 'Dropped Out'),
    ]
    
    TYPE_CHOICES = [
        ('NEW', 'New Student'),
        ('OLD', 'Returning Student'),
    ]
    
    student = models.ForeignKey(
        Student, 
        on_delete=models.CASCADE, 
        related_name='year_statuses'
    )
    academic_year = models.CharField(max_length=10)
    previous_class = models.ForeignKey(
        'Class', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='previous_class_statuses'
    )
    new_class = models.ForeignKey(
        'Class', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='new_class_statuses'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    previous_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    new_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    archived_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-academic_year', 'student__last_name', 'student__first_name']
        unique_together = ['student', 'academic_year']
        verbose_name_plural = "Student Year Statuses"
    
    def __str__(self):
        return f"{self.student.full_name} - {self.academic_year} - {self.get_status_display()}"
    
    @property
    def status_color(self):
        colors = {
            'PROMOTED': 'green',
            'REPEAT': 'orange',
            'DEMOTED': 'red',
            'GRADUATED': 'blue',            
            'LEVEL': 'gray',
            'DROPOUT': 'darkred',
            
        }
        return colors.get(self.status, 'black')
