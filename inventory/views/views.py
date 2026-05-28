from rest_framework import generics
from inventory.models import Medicine
from inventory.serializers import MedicineSerializer
from rest_framework.permissions import AllowAny # Herkese izin ver
import pandas as pd
from django.utils.decorators import method_decorator #Cache Backend
from django.views.decorators.cache import cache_page
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

# @method_decorator(cache_page(60 * 1), name='dispatch') # CACHE'I KAPATTIK: Sonra açarım proje büyüyünce
class MedicineListCreateView(generics.ListCreateAPIView):
    serializer_class = MedicineSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Medicine.objects.filter(is_active=True)

class MedicineDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Medicine.objects.all()
    serializer_class = MedicineSerializer
    permission_classes = [AllowAny]

    def perform_destroy(self, instance):
        instance.is_active = False
        instance.save()

class MedicineExcelUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser) 
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "Please upload a file."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            df = pd.read_excel(file)
            df = df.where(pd.notnull(df), None)
            
            ilac_listesi = []
            for index, row in df.iterrows():
                # Barkod ve İlaç Adı mecburi
                if not row.get('Barkod') or not row.get('İlaç Adı'):
                    continue
                    
                ilac = Medicine(
                    barcode=str(row.get('Barkod')).strip(),
                    name=row.get('İlaç Adı'),
                    expiry_date=row.get('Son Kullanma Tarihi'),
                    price=row.get('Fiyat') or 0,
                    form_type=row.get('Hap mı Sıvı mı?') or 'TABLET',
                    how_many=row.get('Stok Adedi') or 0,
                    is_active=True  # Silinmiş olsa bile yeniden aktif et
                )
                ilac_listesi.append(ilac)
            
            # update_conflicts=True: varsa günceller (is_active=True yapar), yoksa ekler
            Medicine.objects.bulk_create(
                ilac_listesi,
                update_conflicts=True,
                update_fields=['name', 'expiry_date', 'price', 'form_type', 'how_many', 'is_active'],
                unique_fields=['barcode']
            )
            
            bilgi = f"{len(ilac_listesi)} medicines successfully processed!"
            return Response({"message": bilgi}, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#modelviewset kullanılacak apilerde