from celery import shared_task
from django.core.mail import EmailMessage
from django.conf import settings
from sales.models.models import Sale
from sales.mails.pdf_creator import generate_sale_receipt_pdf
from core.idempotent.mail_idempotent import mail_idempotent

@shared_task(bind=True) # bind=True önemli, self argümanı için
@mail_idempotent(expire=60*60*24) # 24 saat koruma
def send_sale_receipt_email(self, sale_id):
    try:
        sale = Sale.objects.get(id=sale_id)
    except Sale.DoesNotExist:
        return "Sale not found!"

    # Send if customer has email
    if not sale.patient:
        print(f"📧 Customer not found for Sale #{sale_id}. Cancelled.")
        return f"Could not send email for Sale #{sale_id} (No Customer)."
    
    if not sale.patient.email:
        print(f"📧 Customer email address is missing for Sale #{sale_id}. Cancelled.")
        return f"Could not send email for Sale #{sale_id} (No email address)."

    print(f"📧 Sending email for Sale #{sale_id} to: {sale.patient.email}")


    # List purchased medicines
    items_list = ""
    for item in sale.items.all():
        items_list += f"- {item.medicine.name} ({item.quantity} Unit(s)) : {item.price} TRY\n"

    subject = f"E-Invoice: Sale #{sale.id}"
    message = f"""Dear {sale.patient.first_name} {sale.patient.last_name},
Below are the details of the purchase you made from our pharmacy:

{items_list}
--------------------------------
Total Amount: {sale.total_amount} TRY 

We wish you healthy days.
Demirbent Pharmacy"""

    # Generate PDF
    pdf_buffer = generate_sale_receipt_pdf(sale_id)

    # Create EmailMessage Object
    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[sale.patient.email],
    )

    # Attach PDF
    email.attach(f"PHARMACY_RECEIPT_{sale.id}.pdf", pdf_buffer.getvalue(), 'application/pdf')

    # Send
    email.send(fail_silently=False)

    return f"Invoice email (PDF attached) sent to: {sale.patient.email}"
