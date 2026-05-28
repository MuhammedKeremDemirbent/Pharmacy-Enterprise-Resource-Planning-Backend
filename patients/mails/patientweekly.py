from celery import shared_task
from django.core.mail import send_mass_mail
from patients.models import Patient
from django.conf import settings

@shared_task
def send_weekly_campaign_email():
    # E-Postası olan tüm hastalar
    patients = Patient.objects.exclude(email__isnull=True).exclude(email__exact='')
        
    messages = []
    subject = "We Wish You a Healthy Week!"
    
    for patient in patients:
        text = f"""
        Dear {patient.first_name} {patient.last_name},
        
        We wish you a happy and healthy week.
        Please do not forget to track your medications!
        
        Best regards,
        Demirbent Pharmacy
        """
        
        messages.append((subject, text, settings.DEFAULT_FROM_EMAIL, [patient.email]))
    
    if messages:
        send_mass_mail(tuple(messages), fail_silently=False)
        return f"Weekly email sent to {len(messages)} people."
    else:
        return "No recipients found."
