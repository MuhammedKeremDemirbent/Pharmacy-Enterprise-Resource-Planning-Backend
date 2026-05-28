#Mail butonuna basma kodu

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string
from django.core.cache import cache # Redis için
from accounts.models import User

class ForgotPasswordView(APIView):
    def post(self, request):
        email = request.data.get('email')
        
        if not email:
            return Response({"error": "E-posta adresi gereklidir."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Dürüst Yaklaşım: Kullanıcı yoksa hata döneriz
            return Response({"error": "No registered user found with this email address."}, status=status.HTTP_404_NOT_FOUND)

        #Token Oluştur 
        token = get_random_string(length=32)
        
        #Redis'e Kaydet 
        redis_key = f"password_reset_{token}"
        cache.set(redis_key, user.id, timeout=900) # 900 sn = 15 dk

        # Mail Linki Oluştur
        reset_link = f"http://localhost:3000/reset-password?token={token}"
        
        subject = "Pharmacy ERP - Password Reset Request"
        message = f"""
        Hello {user.first_name},

        # subject = "Eczane ERP - Şifre Sıfırlama Talebi" # Subject and message will be handled by the Celery task
        # message = f"""
        # Merhaba {user.first_name},

        # Şifrenizi sıfırlamak için aşağıdaki linke tıklayın:
        # {reset_link}

        # Bu link 15 dakika geçerlidir.
        # Eğer bu talebi siz yapmadıysanız, lütfen dikkate almayınız.
        # """
        
        # Celery Task Çağır (Async - apply_async ile)
        from accounts.tasks import send_password_reset_email
        send_password_reset_email.apply_async(args=[email, reset_link, user.first_name])

        return Response({"message": "Password reset link has been sent to your email address."}, status=status.HTTP_200_OK)

class ResetPasswordView(APIView):
    def post(self, request):
        token = request.data.get('token')
        new_password = request.data.get('new_password')
        
        if not token or not new_password:
            return Response({"error": "Token and new password are required."}, status=status.HTTP_400_BAD_REQUEST)
        
        #Redis'ten Token'ı Kontrol Et
        redis_key = f"password_reset_{token}"
        user_id = cache.get(redis_key)
        
        if not user_id:
            return Response({"error": "Invalid or expired link."}, status=status.HTTP_400_BAD_REQUEST)
        
        #Kullanıcıyı Bul ve Şifresini Değiştir
        try:
            user = User.objects.get(id=user_id)
            user.set_password(new_password)
            user.save()
            
            #Token'ı Sil (Tek kullanımlık olsun)
            cache.delete(redis_key)
            
            return Response({"message": "Your password has been successfully changed. You can log in with your new password."}, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
