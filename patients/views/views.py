import pandas as pd
from rest_framework import generics
from patients.models import Patient
from patients.serializers import PatientSerializer

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

#Hazır şablon ve Patient.objects.all() ile jsona çevirir.
class PatientListCreateView(generics.ListCreateAPIView):  #modelwiewsetler var
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer

class PatientRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer


class PatientExcelUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser) 
    def post(self, request, *args, **kwargs):
        file = request.FILES.get('file')
        
        if not file:
            return Response({"error": "Please upload a file."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
         
            df = pd.read_excel(file)
            
            df = df.where(pd.notnull(df), None)
            
            hasta_listesi = []
            
            for index, row in df.iterrows():
                if not row.get('Ad') or not row.get('Soyad'):
                     continue
                    
                hasta = Patient(
                    tc=row.get('TC'),
                    first_name=row.get('Ad'),
                    last_name=row.get('Soyad'),
                    phone_number=row.get('Telefon'),
                    email=row.get('E-Posta'),
                    address=row.get('Adres')
                )
                hasta_listesi.append(hasta)
            
            Patient.objects.bulk_create(hasta_listesi, ignore_conflicts=True)
            
            bilgi = f"{len(hasta_listesi)} patients successfully added!"
            return Response({"message": bilgi}, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({"error": f"An error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ignore_conflicts=True (Çakışma Kalkanı),continue,.get()
