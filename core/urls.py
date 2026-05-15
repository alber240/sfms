from django.urls import path
from . import views

urlpatterns = [
    path('exchange-rate/', views.exchange_rate_settings, name='exchange_rate_settings'),
]
