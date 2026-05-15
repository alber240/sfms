from django.urls import path
from . import views

urlpatterns = [
    path('', views.expense_list, name='expense_list'),
    path('add/', views.expense_add, name='expense_add'),
    path('delete/<int:pk>/', views.expense_delete, name='expense_delete'),
    path('view-photo/<int:pk>/', views.expense_view_photo, name='expense_view_photo'),
]
