from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core import views

urlpatterns = [
    path('check-update/', views.check_update, name='check_update'),
    path('admin/', admin.site.urls),
    path('', views.login_view, name='login'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('principal/', views.principal_dashboard, name='principal_dashboard'),
    path('portal/', views.principal_portal, name='principal_portal'),
    path('logout/', views.logout_view, name='logout'),
    path('undo/', views.undo_last_transaction, name='undo'),
    path('check-reminder/', views.check_reminder, name='check_reminder'),
    path('dismiss-reminder/', views.dismiss_reminder, name='dismiss_reminder'),
    path('set-language/', views.set_language, name='set_language'),
    path('change-password/', views.change_password, name='change_password'),
    path('students/', include('students.urls')),
    path('receipts/', include('receipts.urls')),
    path('expenses/', include('expenses.urls')),
    path('fees/', include('fees.urls')),
    path('settings/', include('settings_app.urls')),
    path('settings/', include('core.urls')),
    path('backup/', views.backup_view, name='backup_view'),
    path('backup/auto-backup/', views.auto_backup_endpoint, name='auto_backup_endpoint'),
    path('cloud-sync/', views.cloud_sync_settings, name='cloud_sync_settings'),
    path('cloud-sync/now/', views.cloud_sync_now, name='cloud_sync_now'),
    path('reports/', include('reports.urls')),
    path('inventory/', include('inventory.urls')),
    path('payroll/', include('payroll.urls')),
    path('process-emails/', views.check_and_send_emails, name='process_emails'),
    path('mobile/', views.mobile_principal_dashboard, name='mobile_principal_dashboard'),
    path('api/license-info/', views.license_info_api, name='license_info_api'),

# Recovery URLs
path('recover/', views.recover_data, name='recover_data'),
path('restore-usb/', views.restore_from_usb, name='restore_from_usb'),
path('cloud-sync/', views.cloud_sync_settings, name='cloud_sync_settings'),
path('cloud-sync/now/', views.cloud_sync_now, name='cloud_sync_now'),

# Archive URLs
path('archives/', views.archive_list, name='archive_list'),
path('archives/archive-now/', views.archive_year_now, name='archive_year_now'),
path('archives/archive-all/', views.archive_all_now, name='archive_all_now'),
path('archives/view/<str:academic_year>/', views.view_archive, name='view_archive'),
path('archives/download/<str:academic_year>/', views.download_archive, name='download_archive'),

# Data Export URLs
path('export/', views.export_dashboard, name='export_dashboard'),
path('export/<str:export_type>/', views.export_data, name='export_data'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
