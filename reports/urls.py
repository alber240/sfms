from django.urls import path
from . import views

urlpatterns = [
    path('', views.reports_dashboard, name='reports_dashboard'),
    path('daily-cash/', views.daily_cash_report, name='daily_cash'),
    path('weekly/', views.weekly_collections, name='weekly'),
    path('termly/', views.termly_summary, name='termly'),
    path('arrears/', views.arrears_report, name='arrears'),
    path('missing-receipts/', views.missing_receipts_report, name='missing_receipts'),
    path('export-audit/', views.export_audit_summary, name='export_audit'),
    path('export-receipts/', views.export_receipts_excel, name='export_receipts'),
    path('whatsapp-reminders/', views.send_whatsapp_reminders, name='whatsapp_reminders'),
]
