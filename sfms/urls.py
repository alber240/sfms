from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.login_view, name='login'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('principal/', views.principal_dashboard, name='principal_dashboard'),
    path('logout/', views.logout_view, name='logout'),
    path('undo/', views.undo_last_transaction, name='undo'),
    path('check-reminder/', views.check_reminder, name='check_reminder'),
    path('dismiss-reminder/', views.dismiss_reminder, name='dismiss_reminder'),
    path('students/', include('students.urls')),
    path('receipts/', include('receipts.urls')),
    path('expenses/', include('expenses.urls')),
    path('fees/', include('fees.urls')),
    path('settings/', include('settings_app.urls')),
    path('settings/', include('core.urls')),
    path('reports/', include('reports.urls')),
    path('payroll/', include('payroll.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)




