import base64
import io
import qrcode


from django.conf import settings
from django.utils import timezone


import requests




def generate_qr_base64(payload: str) -> str:
    """Create a QR code PNG and return base64 string (data:image/png;base64,...)."""
    img = qrcode.make(payload)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    b64 = base64.b64encode(buf.getvalue()).decode('ascii')
    return f"data:image/png;base64,{b64}"




def send_to_gateway(gateway_endpoint: str, payload: dict, headers: dict = None, timeout: int = 8):
    """Micro wrapper for calling external payment gateways / URL shorteners, etc."""
    headers = headers or {}
    resp = requests.post(gateway_endpoint, json=payload, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json()