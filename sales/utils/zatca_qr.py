import base64
from io import BytesIO
from datetime import datetime
from qrcode import make as make_qr

def generate_invoice_qr_base64(seller_name, vat_number, timestamp, invoice_total, vat_total):
    """
    توليد QR Code حسب متطلبات هيئة الزكاة والضريبة والجمارك (ZATCA)
    """
    def to_bytes(tag, value):
        value_bytes = value.encode('utf-8')
        tag_bytes = bytes([tag])
        length_bytes = bytes([len(value_bytes)])
        return tag_bytes + length_bytes + value_bytes

    data = b''.join([
        to_bytes(1, seller_name),
        to_bytes(2, vat_number),
        to_bytes(3, timestamp),
        to_bytes(4, invoice_total),
        to_bytes(5, vat_total),
    ])

    qr_img = make_qr(data)
    buffer = BytesIO()
    qr_img.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('utf-8')
