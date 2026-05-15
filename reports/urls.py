from django.urls import path
from . import views

urlpatterns = [
    path('', views.reports_dashboard, name='reports_dashboard'),
    path('daily-cash/', views.daily_cash_report, name='daily_cash_report'),
    path('weekly-collections/', views.weekly_collections, name='weekly_collections'),
    path('termly-summary/', views.termly_summary, name='termly_summary'),
    path('arrears/', views.arrears_report, name='arrears_report'),
]
