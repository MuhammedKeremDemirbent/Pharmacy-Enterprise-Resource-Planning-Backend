from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from inventory.models import Medicine

@shared_task
def check_stock_metrics():
    """
    10'dan az kalan ilaçları raporlar ve mail atar.
    """
    print("Stock Control Started")
    
    # Less than 10
    low_stock_medicines = Medicine.objects.filter(how_many__lt=10)
    
    if low_stock_medicines.exists():
        count = low_stock_medicines.count()
        print(f"ATTENTION! {count} medicines are at a critical level:")
        
        # Prepare Email Content
        message_body = f"ATTENTION! {count} medicines are running low in stock.\n\nLow Stock Medicines:\n"
        for med in low_stock_medicines:
            line = f"- {med.name} (Remaining: {med.how_many})"
            print(line)
            message_body += line + "\n"
            
        message_body += "\nPlease initiate the procurement process."

        # Mailgun or AWS in the future instead of Mailpit
        send_mail(
            subject="URGENT: Critical Stock Alert",
            message=message_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=['keremdmrbnt03@gmail.com'],
            fail_silently=False,
        ) 
        return f"Email Sent: {count} medicines low."
        
    else:
        print("Stock status is great! No missing medicines.")
        
    return "Control Completed (No Issue)"
