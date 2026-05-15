from django.urls import path
from . import views

urlpatterns = [
    path('', views.student_list, name='student_list'),
    path('add/', views.student_add, name='student_add'),
    path('<int:pk>/', views.student_detail, name='student_detail'),
    path('<int:pk>/edit/', views.student_edit, name='student_edit'),
    path('<int:pk>/delete/', views.student_delete, name='student_delete'),
    # Class management URLs
    path('classes/', views.class_list, name='class_list'),
    path('classes/add/', views.class_add, name='class_add'),
    path('classes/<int:pk>/edit/', views.class_edit, name='class_edit'),
    path('classes/<int:pk>/delete/', views.class_delete, name='class_delete'),
]
