from django.urls import path
from . import views

urlpatterns = [
    path('', views.staff_list, name='staff_list'),
    path('add/', views.staff_add, name='staff_add'),
    path('edit/<int:pk>/', views.staff_edit, name='staff_edit'),
    path('delete/<int:pk>/', views.staff_delete, name='staff_delete'),
    path('history/<int:staff_id>/', views.staff_payroll_history, name='staff_payroll_history'),
    path('advance/<int:staff_id>/', views.staff_advance, name='staff_advance'),
    path('process/', views.process_payroll, name='process_payroll'),
    path('pay-staff/<int:staff_id>/', views.pay_staff_individual, name='pay_staff_individual'),
    path('history/', views.payroll_history, name='payroll_history'),
    path('detail/<int:pk>/', views.payroll_detail, name='payroll_detail'),
    path('receipt/<int:entry_id>/', views.payroll_receipt_print, name='payroll_receipt_print'),
    path('bulk-receipts/<int:period_id>/', views.payroll_bulk_receipts_print, name='payroll_bulk_receipts_print'),
    path('bulk-individual/<int:period_id>/', views.payroll_bulk_individual_receipts, name='payroll_bulk_individual_receipts'),
]





