from django.urls import path
from . import views

urlpatterns = [
    path('exchange-rate/', views.exchange_rate_settings, name='exchange_rate_settings'),
    path('school-info/', views.school_info_settings, name='school_info'),
]
