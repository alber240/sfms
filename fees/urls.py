from django.urls import path
from . import views

urlpatterns = [
    # Fee Structure
    path('fee-matrix/', views.fee_structure_matrix, name='fee_structure_matrix'),
    path('installments/', views.installment_plans, name='installment_plans'),
    
    # Academic Sessions
    path('academic-sessions/', views.academic_session_settings, name='academic_session_settings'),
    path('add-academic-session/', views.add_academic_session, name='add_academic_session'),
    
    # Fee Settings (redirect)
    path('settings/', views.fee_settings_dashboard, name='fee_settings'),
    
    # Reminders
    path('reminders/', views.check_installment_reminders, name='fee_reminders'),
    
    # Auto Assign
    path('auto-assign-v2/', views.auto_assign_fees_v2, name='auto_assign_fees_v2'),
    
    # Scholarships
    path('scholarships/', views.scholarship_management, name='scholarship_management'),
    path('add-scholarship/', views.add_scholarship, name='add_scholarship'),
    path('edit-scholarship/<int:pk>/', views.edit_scholarship, name='edit_scholarship'),
    path('delete-scholarship/<int:pk>/', views.delete_scholarship, name='delete_scholarship'),
    path('assign-scholarship/<int:student_id>/', views.assign_scholarship, name='assign_scholarship'),
]
