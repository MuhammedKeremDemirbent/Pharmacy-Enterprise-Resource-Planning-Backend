from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from procurement.models import Procurement

@shared_task
def send_supplier_order_email(supplier_id, order_items, custom_message=None, custom_subject=None):
    """
    Tedarikçiye sipariş veya mesaj gönderir.
    """
    try:
        supplier = Procurement.objects.get(id=supplier_id)
    except Procurement.DoesNotExist:
        return "Supplier not found."
        
    if not supplier.email:
        return f"Email address not registered for {supplier.name}."
        
    items_text = ""
    if order_items:
        items_text += "Order List:\n"
        for item in order_items:
            name = item.get('name') if isinstance(item, dict) else item
            quantity = item.get('quantity', 1) if isinstance(item, dict) else 1
            items_text += f"- {name} : {quantity} Box(es)\n"
            
    # Use custom subject if provided, otherwise default
    subject = custom_subject if custom_subject else f"Order Request - Demirbent Pharmacy"

    if custom_message:
        body_text = custom_message
    else:
        body_text = "We kindly request the following products to be sent to us as soon as possible."

    final_message = f"""Dear {supplier.name} Representative,

{body_text}

{items_text}

Best regards,
Demirbent Pharmacy"""
    
    send_mail(
        subject=subject,
        message=final_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[supplier.email],
        fail_silently=False,
    )
    
    return f"Email sent: {supplier.email}"
