from django.urls import path
from . import views

urlpatterns = [
    path('', views.settings_dashboard, name='settings_dashboard'),
    path('add-category/', views.add_category, name='add_category'),
    path('edit-category/<int:pk>/', views.edit_category, name='edit_category'),
    path('delete-category/<int:pk>/', views.delete_category, name='delete_category'),
    # fee-settings URL removed - use /fees/settings/ instead
]
