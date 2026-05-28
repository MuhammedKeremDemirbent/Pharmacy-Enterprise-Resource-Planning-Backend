from celery import shared_task

from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Count
from django.core.mail import send_mail
from django.conf import settings
from inventory.models import Medicine
from sales.models import Sale, SaleItem

@shared_task
def send_weekly_report():
    """
    Haftalık Satış ve Stok Raporunu Hazırlar ve Gönderir.
    """
    print("📊 Preparing Weekly Report...")
    
    # Date Range 1 week
    today = timezone.now()
    last_week = today - timedelta(days=7)
    
    # Weekly Sales Data
    weekly_sales = Sale.objects.filter(created_at__gte=last_week)
    total_revenue = weekly_sales.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    total_orders = weekly_sales.count()
    
    # Critical Stocks
    low_stock_count = Medicine.objects.filter(how_many__lt=10).count()
    
    # En Çok Satan 3 İlaç (Opsiyonel ama şık durur)
    top_items = SaleItem.objects.filter(sale__created_at__gte=last_week)\
        .values('medicine__name')\
        .annotate(total_qty=Sum('quantity'))\
        .order_by('-total_qty')[:3]

    # Email Content Creation
    message = f"""
    Dear Manager,
    
    Here is the weekly performance report for your pharmacy ({last_week.strftime('%d.%m')} - {today.strftime('%d.%m')}):
    
    💰 Financial Status:
    ------------------
    Total Revenue: {total_revenue:,.2f} TRY
    Total Number of Sales: {total_orders}
    
    📦 Stock Status:
    ------------------
    Number of Medicines at Critical Level: {low_stock_count}
    
    🏆 Stars of the Week (Top Sellers):
    ------------------
    """
    
    for item in top_items:
        message += f"- {item['medicine__name']}: {item['total_qty']} units\n"
        
    message += "\nWe wish you a good week.\nPharmacy ERP System"

    # Send Email
    send_mail(
        subject=f"Weekly Report: {today.strftime('%d.%m.%Y')}",
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=['[EMAIL_ADDRESS]'], # You can set your own email here
        fail_silently=False,
    )
    
    return f"Weekly Report Sent. Revenue: {total_revenue} TRY"
