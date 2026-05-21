from django.urls import path
from . import views

urlpatterns = [
    path('', views.expense_list, name='expense_list'),
    path('add/', views.expense_add, name='expense_add'),
    path('delete/<int:pk>/', views.expense_delete, name='expense_delete'),
    path('view-photo/<int:pk>/', views.expense_view_photo, name='expense_view_photo'),

    path('approvals/', views.expense_approval_list, name='expense_approval_list'),
    path('approve/<int:pk>/', views.expense_approve, name='expense_approve'),
    path('reject/<int:pk>/', views.expense_reject, name='expense_reject'),
    path('mark-paid/<int:pk>/', views.expense_mark_paid, name='expense_mark_paid'),
]
