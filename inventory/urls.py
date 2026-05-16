from django.urls import path
from . import views

urlpatterns = [
    path('', views.inventory_list, name='inventory_list'),
    path('add/', views.inventory_add, name='inventory_add'),
    path('edit/<int:pk>/', views.inventory_edit, name='inventory_edit'),
    path('delete/<int:pk>/', views.inventory_delete, name='inventory_delete'),
    path('issue/<int:pk>/', views.inventory_issue, name='inventory_issue'),
    # Category management
    path('categories/', views.inventory_category_list, name='inventory_category_list'),
    path('categories/add/', views.inventory_category_add, name='inventory_category_add'),
    path('categories/edit/<int:pk>/', views.inventory_category_edit, name='inventory_category_edit'),
    path('categories/delete/<int:pk>/', views.inventory_category_delete, name='inventory_category_delete'),
]