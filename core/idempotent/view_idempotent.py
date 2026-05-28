import hashlib
import json
from functools import wraps
from django.core.cache import cache
from rest_framework.response import Response
from rest_framework import status

#checkout.py için yaptık
def idempotent(timeout=300):
    """
    Idempotency Decorator
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
           
            key = request.headers.get('Idempotency-Key') or request.META.get('HTTP_IDEMPOTENCY_KEY')
            
            # DEBUG: Gelen Header'ı Görelim
            print(f"🔍 IDEMPOTENCY CHECK: Key={key}, User={request.user}")

            if not key:
                print("⚠️ Idempotency Key YOK! İşlem korumasız devam ediyor.")
                return view_func(request, *args, **kwargs)

            # Redis Key Oluşturma
            user_id = request.user.id if request.user.is_authenticated else 'anon'
            cache_key = f"idempotency_{user_id}_{key}"
            
            # Cache Kontrolü (Daha önce başarıyla işlenmişse direkt dön)
            cached_response = cache.get(cache_key)
            if cached_response:
                print(f"🛑 IDEMPOTENCY: {key} daha önce işlenmiş! Eski cevap dönülüyor.")
                return Response(cached_response['data'], status=cached_response['status'])

            # Yarış Koşulunu (Race Condition) önlemek için Dağıtık Kilit (Distributed Lock) oluşturuyoruz
            lock_key = f"idempotency_lock_{user_id}_{key}"
            # cache.add (Redis SETNX) atomik bir işlemdir. Kilit 30 saniye sonra otomatik düşer (deadlock önlemi).
            is_locked = not cache.add(lock_key, "processing", timeout=30)
            if is_locked:
                print(f"🛑 IDEMPOTENCY: {key} şu an işlemde! 409 Conflict dönülüyor.")
                return Response(
                    {"error": "Bu istek şu anda işleniyor. Lütfen bekleyin."}, 
                    status=status.HTTP_409_CONFLICT
                )

            try:
                response = view_func(request, *args, **kwargs)

                # Sadece başarılı (2xx) cevapları cache'e kaydediyoruz
                if 200 <= response.status_code < 300:
                    print(f"✅ IDEMPOTENCY: {key} başarıyla işlendi ve kaydedildi. (Süre: {timeout}sn)")
                    response_data = {
                        'data': response.data,
                        'status': response.status_code
                    }
                    cache.set(cache_key, response_data, timeout=timeout)
                    
                return response
            finally:
                # Kilit her koşulda (hata alınsa bile) serbest bırakılmalıdır
                cache.delete(lock_key)
            
        return _wrapped_view
    return decorator
