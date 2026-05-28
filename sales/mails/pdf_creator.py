import io
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from sales.models.models import Sale, SaleItem

# Türkçe karakter desteği için fontları tanımlıyoruz
# Docker içinde /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf yolunda yüklü olacak
pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))

def generate_sale_receipt_pdf(sale_id):
    sale = Sale.objects.get(id=sale_id)
    items = sale.items.all()
    
    # Yerel saate çevir (İstanbul GMT+3)
    local_time = timezone.localtime(sale.created_at)

    buffer = io.BytesIO()
    # Modern görünüm için kenar boşluklarını 36pt (0.5 inç) olarak ayarlıyoruz
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    elements = []
    
    # Stil Tanımlamaları
    styles = getSampleStyleSheet()
    
    brand_title_style = ParagraphStyle(
        'BrandTitle',
        parent=styles['Normal'],
        fontName='DejaVuSans-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#1A365D') # Kurumsal Koyu Lacivert
    )
    
    brand_subtitle_style = ParagraphStyle(
        'BrandSubtitle',
        parent=styles['Normal'],
        fontName='DejaVuSans',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#718096') # Kül Grisi
    )
    
    invoice_title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Normal'],
        fontName='DejaVuSans-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#2D3748'),
        alignment=2 # Sağ Hizalama
    )
    
    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Normal'],
        fontName='DejaVuSans-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#2B6CB0') # Primer Mavi
    )
    
    body_normal_style = ParagraphStyle(
        'BodyNormal',
        parent=styles['Normal'],
        fontName='DejaVuSans',
        fontSize=9,
        leading=14,
        textColor=colors.HexColor('#4A5568')
    )
    
    footer_style = ParagraphStyle(
        'FooterText',
        parent=styles['Normal'],
        fontName='DejaVuSans',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#A0AEC0'),
        alignment=1 # Orta Hizalama
    )

    # 1. Başlık Bölümü (Eczane Bilgileri solda, Fiş Başlığı sağda)
    header_data = [
        [
            Paragraph("DEMIRBENT PHARMACY", brand_title_style),
            Paragraph("SALES RECEIPT", invoice_title_style)
        ],
        [
            Paragraph("Healthcare & Wellness Services", brand_subtitle_style),
            Paragraph("", brand_subtitle_style)
        ]
    ]
    # Toplam kullanılabilir genişlik: A4 (595pt) - Kenar boşlukları (72pt) = 523pt
    header_table = Table(header_data, colWidths=[300, 223])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(header_table)
    
    # Başlığın altına dekoratif kurumsal çizgi ekliyoruz
    elements.append(Spacer(1, 15))
    divider_table = Table([[""]], colWidths=[523], rowHeights=[2])
    divider_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, -1), 1.5, colors.HexColor('#1A365D')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(divider_table)
    elements.append(Spacer(1, 15))

    # 2. Metadata / Fiş Bilgileri Bölümü
    patient_info = ""
    if sale.patient:
        patient_name = f"{sale.patient.first_name} {sale.patient.last_name}"
        phone = sale.patient.phone_number or "N/A"
        email = sale.patient.email or "N/A"
        patient_info = f"<b>Name:</b> {patient_name}<br/><b>Phone:</b> {phone}<br/><b>Email:</b> {email}"
    else:
        patient_info = "<b>Name:</b> Walk-in Customer"

    staff_name = sale.user.username if sale.user else "System Admin"
    invoice_details = f"<b>Receipt No:</b> #{sale.id}<br/><b>Date:</b> {local_time.strftime('%d.%m.%Y %H:%M')}<br/><b>Staff:</b> {staff_name}"

    metadata_data = [
        [
            Paragraph("BILLED TO", section_title_style),
            Paragraph("RECEIPT DETAILS", section_title_style)
        ],
        [
            Paragraph(patient_info, body_normal_style),
            Paragraph(invoice_details, body_normal_style)
        ]
    ]
    
    metadata_table = Table(metadata_data, colWidths=[261, 262])
    metadata_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(metadata_table)
    elements.append(Spacer(1, 25))

    # 3. İlaçlar Listesi Tablosu
    table_header_style = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='DejaVuSans-Bold',
        fontSize=9,
        leading=13,
        textColor=colors.white
    )
    
    table_cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='DejaVuSans',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#2D3748')
    )
    
    table_cell_center_style = ParagraphStyle(
        'TableCellCenter',
        parent=table_cell_style,
        alignment=1
    )
    
    table_cell_right_style = ParagraphStyle(
        'TableCellRight',
        parent=table_cell_style,
        alignment=2
    )

    data = [
        [
            Paragraph("Medicine Name", table_header_style), 
            Paragraph("Qty", table_header_style), 
            Paragraph("Unit Price", table_header_style), 
            Paragraph("Total", table_header_style)
        ]
    ]
    
    for item in items:
        data.append([
            Paragraph(item.medicine.name, table_cell_style),
            Paragraph(str(item.quantity), table_cell_center_style),
            Paragraph(f"{item.price} TRY", table_cell_right_style),
            Paragraph(f"{item.quantity * item.price} TRY", table_cell_right_style)
        ])
        
    total_label_style = ParagraphStyle(
        'TotalLabel',
        parent=styles['Normal'],
        fontName='DejaVuSans-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1A365D'),
        alignment=2
    )
    total_val_style = ParagraphStyle(
        'TotalVal',
        parent=styles['Normal'],
        fontName='DejaVuSans-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1A365D'),
        alignment=2
    )
    
    data.append([
        "",
        "",
        Paragraph("GRAND TOTAL:", total_label_style),
        Paragraph(f"{sale.total_amount} TRY", total_val_style)
    ])

    # Sütun Genişlikleri: Toplam 523pt (İlaç Adı=263pt, Adet=60pt, Birim Fiyat=100pt, Toplam=100pt)
    table = Table(data, colWidths=[263, 60, 100, 100])
    
    t_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1A365D')), # Lacivert başlık
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]
    
    # Alternatif satır arka planı (Zebra desenli modern görünüm)
    for i in range(1, len(items) + 1):
        bg_color = colors.HexColor('#F7FAFC') if i % 2 == 0 else colors.white
        t_style.append(('BACKGROUND', (0, i), (-1, i), bg_color))
        # İnce yatay çizgi
        t_style.append(('LINEBELOW', (0, i), (-1, i), 0.5, colors.HexColor('#E2E8F0')))
        
    t_style.extend([
        ('SPAN', (0, -1), (1, -1)), # İlk iki sütunu GRAND TOTAL için birleştir
        ('TOPPADDING', (0, -1), (-1, -1), 15),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 15),
    ])
    
    table.setStyle(TableStyle(t_style))
    elements.append(table)
    
    # 4. Alt Bilgi (Footer)
    elements.append(Spacer(1, 40))
    elements.append(Paragraph("Thank you for choosing Demirbent Pharmacy! Stay healthy.", footer_style))

    doc.build(elements)
    buffer.seek(0)
    return buffer
