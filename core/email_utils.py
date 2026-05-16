import logging
from django.core.mail import send_mail
from django.conf import settings
from .models import EmailQueue, SchoolSetting
from datetime import datetime
import socket

logger = logging.getLogger(__name__)

def is_internet_available():
    """Check if internet is available by attempting to connect to Google DNS"""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False

def send_payroll_receipt_email(staff, payroll_entry, payroll_period):
    """Send payroll receipt to staff email - queues if offline"""
    
    if not staff.email:
        return False, "No email address for staff"
    
    # Get school settings
    school_name_setting = SchoolSetting.objects.filter(key='school_name').first()
    accountant_name_setting = SchoolSetting.objects.filter(key='accountant_name').first()
    school_name = school_name_setting.value if school_name_setting else 'SFMS SCHOOL'
    accountant_name = accountant_name_setting.value if accountant_name_setting else 'Accountant'
    
    subject = f"Payroll Receipt - {payroll_period.get_month_display()} {payroll_period.year}"
    
    # Create HTML email content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; }}
            .receipt {{ max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; }}
            .header {{ text-align: center; border-bottom: 2px solid #1e3c72; padding-bottom: 10px; }}
            .school-name {{ font-size: 24px; font-weight: bold; color: #1e3c72; }}
            .title {{ font-size: 18px; margin-top: 10px; }}
            .info-row {{ margin: 10px 0; padding: 5px; border-bottom: 1px solid #eee; }}
            .amount {{ font-size: 20px; font-weight: bold; text-align: center; margin: 20px 0; padding: 10px; background: #f0f0f0; }}
            .footer {{ margin-top: 30px; text-align: center; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="receipt">
            <div class="header">
                <div class="school-name">{school_name}</div>
                <div class="title">PAYROLL PAYMENT RECEIPT</div>
            </div>
            <div class="info-row"><strong>Staff Name:</strong> {staff.name}</div>
            <div class="info-row"><strong>Staff ID:</strong> {staff.staff_id}</div>
            <div class="info-row"><strong>Position:</strong> {staff.position}</div>
            <div class="info-row"><strong>Payment Period:</strong> {payroll_period.get_month_display()} {payroll_period.year}</div>
            <div class="info-row"><strong>Base Salary:</strong> {payroll_entry.base_salary_lrd} LRD / {payroll_entry.base_salary_usd} USD</div>
            <div class="amount">NET PAY: {payroll_entry.net_pay_lrd} LRD</div>
            <div class="footer">
                <p>This is a computer-generated receipt.</p>
                <p>Thank you for your service!<br>{accountant_name}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Plain text version
    text_content = f"""
{school_name}
PAYROLL RECEIPT

Staff Name: {staff.name}
Staff ID: {staff.staff_id}
Position: {staff.position}
Payment Period: {payroll_period.get_month_display()} {payroll_period.year}

NET PAY: {payroll_entry.net_pay_lrd} LRD

Thank you for your service!
{accountant_name}
"""
    
    # Check if internet is available
    if is_internet_available():
        try:
            send_mail(
                subject=subject,
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[staff.email],
                html_message=html_content,
                fail_silently=False,
            )
            return True, "Email sent successfully"
        except Exception as e:
            # If sending fails, queue it
            EmailQueue.objects.create(
                to_email=staff.email,
                subject=subject,
                message=text_content,
                html_message=html_content,
                status='PENDING',
                error_message=str(e)
            )
            return False, f"No internet: Email queued. Will send when online."
    else:
        # No internet - queue the email
        EmailQueue.objects.create(
            to_email=staff.email,
            subject=subject,
            message=text_content,
            html_message=html_content,
            status='PENDING'
        )
        return False, "No internet: Email queued. Will send when online."

def process_email_queue():
    """Process pending emails when internet is available"""
    if not is_internet_available():
        return 0, "No internet"
    
    pending_emails = EmailQueue.objects.filter(status='PENDING')
    sent_count = 0
    
    for email in pending_emails:
        try:
            send_mail(
                subject=email.subject,
                message=email.message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email.to_email],
                html_message=email.html_message,
                fail_silently=False,
            )
            email.status = 'SENT'
            email.sent_at = datetime.now()
            email.save()
            sent_count += 1
        except Exception as e:
            email.attempts += 1
            email.error_message = str(e)
            if email.attempts >= 3:
                email.status = 'FAILED'
            email.save()
    
    return sent_count, f"Sent {sent_count} emails"
