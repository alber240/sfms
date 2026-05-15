from django.urls import path
from . import views

urlpatterns = [
    path('payment/<int:student_id>/', views.payment_entry, name='payment_entry'),
    path('payment/', views.payment_entry, name='payment_entry'),
    path('quick/', views.quick_payment, name='quick_payment'),
    path('print/<int:receipt_id>/', views.receipt_print, name='receipt_print'),
    path('batch/', views.batch_payment, name='batch_payment'),
]

