#Maili SMTP ile Gönderme Kodu

from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings

@shared_task
def send_password_reset_email(email, reset_link, user_first_name):
    """
    Şifre sıfırlama mailini asenkron olarak gönderir.
    """
    subject = "Pharmacy ERP - Password Reset Request"
    message = f"""
    Hello {user_first_name},

    Click the link below to reset your password:
    {reset_link}

    This link is valid for 15 minutes.
    If you did not make this request, please ignore this email.
    """
    
    try:
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False)
        return f"Password reset email sent to: {email}"
    except Exception as e:
        return f"Failed to send email: {str(e)}"


#Asenkron-celery Mantığı ile Yapıldı