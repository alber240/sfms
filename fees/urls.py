from django.urls import path
from . import views

urlpatterns = [
    # ============================================================
    # FEE STRUCTURE MATRIX
    # ============================================================
    path('fee-matrix/', views.fee_structure_matrix, name='fee_structure_matrix'),
    path('fee-matrix/', views.fee_structure_matrix, name='fee_matrix'),
    path('installments/', views.installment_plans, name='installment_plans'),
    
    # ============================================================
    # ACADEMIC SESSIONS
    # ============================================================
    path('academic-sessions/', views.academic_session_settings, name='academic_session_settings'),
    path('add-academic-session/', views.add_academic_session, name='add_academic_session'),
    
    # ============================================================
    # FEE SETTINGS (Redirect)
    # ============================================================
    path('settings/', views.fee_settings_dashboard, name='fee_settings'),
    
    # ============================================================
    # REMINDERS
    # ============================================================
    path('reminders/', views.check_installment_reminders, name='fee_reminders'),
    
    # ============================================================
    # AUTO ASSIGN FEES
    # ============================================================
    path('auto-assign-v2/', views.auto_assign_fees_v2, name='auto_assign_fees_v2'),
    
    # ============================================================
    # SCHOLARSHIPS
    # ============================================================
    path('scholarships/', views.scholarship_management, name='scholarship_management'),
    path('add-scholarship/', views.add_scholarship, name='add_scholarship'),
    path('edit-scholarship/<int:pk>/', views.edit_scholarship, name='edit_scholarship'),
    path('delete-scholarship/<int:pk>/', views.delete_scholarship, name='delete_scholarship'),
    path('assign-scholarship/<int:student_id>/', views.assign_scholarship, name='assign_scholarship'),
    
    # ============================================================
    # FEE CATEGORIES
    # ============================================================
    path('manage-categories/', views.manage_categories, name='manage_categories'),
    path('add-category/', views.add_category, name='add_fee_category'),
    path('edit-category/<int:pk>/', views.edit_category, name='edit_fee_category'),
    path('delete-category/<int:pk>/', views.delete_category, name='delete_fee_category'),
    path('inactive-categories/', views.inactive_categories, name='inactive_categories'),
    path('toggle-category/<int:pk>/', views.toggle_category_status, name='toggle_category_status'),
    
    # ============================================================
    # ACADEMIC YEAR MANAGEMENT
    # ============================================================
    path('start-academic-year/', views.start_new_academic_year, name='start_academic_year'),
    path('view-year/', views.view_academic_year, name='view_academic_year_default'),
    path('view-year/<str:year>/', views.view_academic_year, name='view_academic_year'),
    
    # ============================================================
    # YEAR TRANSITION WIZARD
    # ============================================================
    path('year-transition/', views.year_transition, name='year_transition'),
    path('year-transition/step2/', views.year_transition_step2, name='year_transition_step2'),
    path('year-transition/step3/', views.year_transition_step3, name='year_transition_step3'),
]