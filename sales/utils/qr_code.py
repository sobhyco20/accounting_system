import base64
import qrcode
from io import BytesIO


def encode_tlv(tag: int, value: str) -> bytes:
    value_bytes = value.encode('utf-8')
    return bytes([tag]) + bytes([len(value_bytes)]) + value_bytes


def generate_invoice_qr(seller_name, seller_vat, timestamp, total, vat_total):
    tlv_bytes = (
        encode_tlv(1, seller_name) +
        encode_tlv(2, seller_vat) +
        encode_tlv(3, timestamp) +
        encode_tlv(4, str(total)) +
        encode_tlv(5, str(vat_total))
    )
    qr_data = base64.b64encode(tlv_bytes).decode()

    qr = qrcode.make(qr_data)
    buffer = BytesIO()
    qr.save(buffer, format="PNG")
    return buffer.getvalue()
