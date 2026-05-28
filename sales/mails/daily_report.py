from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone
from django.db.models import Sum
from sales.models import Sale
from django.conf import settings

@shared_task
def send_daily_sales_report():

    # timezone.localdate() o anki yerel tarihi (TR saatiyle) verir.
    report_date = timezone.localdate() - timezone.timedelta(days=1)
    

    total_revenue = Sale.objects.filter(created_at__date=report_date).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    
    subject = f"DAILY REPORT: {report_date.strftime('%d.%m.%Y')}"
    message = f"""
    Dear Manager,
    
    Demirbent Pharmacy End of Day Report:
    --------------------------------
    Date: {report_date.strftime('%d.%m.%Y')}
    Total Revenue: {total_revenue} TRY
    
    Best regards.
    """
    
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=['keremdmrbnt03@gmail.com'],
        fail_silently=False,
    )
    
    return f"Daily Report Sent: {total_revenue} TRY"
