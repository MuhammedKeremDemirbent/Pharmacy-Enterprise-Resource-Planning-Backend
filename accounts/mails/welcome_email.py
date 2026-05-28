from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from accounts.models import User

@shared_task
def send_welcome_email(user_id, password):
    """
    Yeni kayıt olan personel için hoşgeldin maili (RegisterEmployeeView için).
    """
    try:
        user = User.objects.get(id=user_id)
        subject = "Welcome to the Pharmacy ERP System!"
        message = f"""
        Hello {user.first_name},
        
        Your staff registration to the Pharmacy ERP system has been completed.
        Login Credentials:
        
        Username: {user.username}
        Password: {password}
        """
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
        return f"Welcome email sent to: {user.email}"
    except User.DoesNotExist:
        return f"User not found: {user_id}"
    except Exception as e:
        return f"Email error: {str(e)}"
