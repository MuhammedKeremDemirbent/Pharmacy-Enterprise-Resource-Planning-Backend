# pyrefly: ignore [missing-import]
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import transaction
from sales.models import Sale, SaleItem
from inventory.models import Medicine
from sales.serializers import CheckoutSerializer
from django.utils.decorators import method_decorator
from core.idempotent.view_idempotent import idempotent

class CheckoutView(APIView):
    
    @method_decorator(idempotent(timeout=300), name='post') #Idempotency 300 saniye
    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        items_data = serializer.validated_data['items']
        patient_id = serializer.validated_data.get('patient_id') 
        
       
        # Group duplicate product IDs to calculate total stock requirements
        grouped_items = {}
        for item in items_data:
            pid = item['product_id']
            qty = item['quantity']
            if qty <= 0:
                return Response({"error": "Quantity must be greater than zero."}, status=status.HTTP_400_BAD_REQUEST)
            grouped_items[pid] = grouped_items.get(pid, 0) + qty

        product_ids = list(grouped_items.keys())

        with transaction.atomic():
            # 1. Batch select all medicines with row-level locks
            medicines = Medicine.objects.select_for_update().filter(id__in=product_ids)
            medicine_map = {m.id: m for m in medicines}

            # 2. Verify all products exist
            for pid in product_ids:
                if pid not in medicine_map:
                    return Response({"error": f"Ürün bulunamadı ID: {pid}"}, status=status.HTTP_404_NOT_FOUND)

            # 3. Verify stock levels in-memory
            for pid, qty in grouped_items.items():
                medicine = medicine_map[pid]
                if medicine.how_many < qty:
                    return Response(
                        {"error": f"{medicine.name} stoğu yetersiz! (Kalan: {medicine.how_many})"}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # 4. Create the Sale record
            user = request.user if request.user.is_authenticated else None
            sale = Sale.objects.create(user=user, patient_id=patient_id)
            
            # 5. In-memory stock deductions and SaleItem preparation
            sale_items = []
            total_price = 0
            
            for item in items_data:
                pid = item['product_id']
                qty = item['quantity']
                medicine = medicine_map[pid]
                
                medicine.how_many -= qty
                sale_items.append(SaleItem(
                    sale=sale,
                    medicine=medicine,
                    quantity=qty,
                    price=medicine.price
                ))
                total_price += medicine.price * qty

            # 6. Bulk update stock in the database
            Medicine.objects.bulk_update(list(medicine_map.values()), ['how_many'])

            # 7. Bulk insert SaleItem records
            SaleItem.objects.bulk_create(sale_items)

            # 8. Update Sale total amount
            sale.total_amount = total_price
            sale.save()

        # Fatura Mailini Kuyruğa Atma
        try:
            from sales.tasks import send_sale_receipt_email
            # apply_async, countdown=2 saniye gecikmeli
            send_sale_receipt_email.apply_async(args=[sale.id], countdown=2)
        except Exception as e:
            print(f"Mail kuyruğa eklenemedi: {e}")

        return Response(
            {"message": "Satış Başarılı!", "sale_id": sale.id, "total": total_price}, 
            status=status.HTTP_201_CREATED
        )
