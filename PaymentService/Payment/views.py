from rest_framework import viewsets, status, mixins
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.conf import settings

from .models import ShopAccount, Payment, Refund
from .serializers import ShopAccountSerializer, PaymentSerializer, RefundSerializer
from .utils import generate_qr_base64, send_to_gateway

class ShopAccountViewSet(viewsets.ModelViewSet):
    queryset = ShopAccount.objects.all()
    serializer_class = ShopAccountSerializer


class PaymentViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    def create(self, request, *args, **kwargs):
        """Initiate a payment. This does NOT process money — it returns payment details (QR or account) and creates Payment record with status 'initiated'."""
        # idempotency support
        idempotency_key = request.headers.get('Idempotency-Key') or request.data.get('idempotency_key')
        if idempotency_key:
            existing = Payment.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                serializer = self.get_serializer(existing)
                return Response(serializer.data, status=status.HTTP_200_OK)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            payment = serializer.save(status='initiated', idempotency_key=idempotency_key)
            # get shop payment info
            sa = ShopAccount.objects.get(shop_id=payment.shop_id)
            response_payload = {
                'payment_id': payment.id,
                'order_id': payment.order_id,
                'amount': str(payment.amount),
                'currency': payment.currency,
            }
            # Prefer returning a QR image if available
            if sa.qr_payload:
                response_payload['qr_image'] = generate_qr_base64(sa.qr_payload)
            else:
                response_payload['account_details'] = sa.account_details

            return Response(response_payload, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='confirm', permission_classes=[])
    def confirm(self, request, pk=None):
        """Endpoint that can be used by internal systems to mark a payment completed (OR used by a webhook)."""
        payment = get_object_or_404(Payment, pk=pk)
        gateway_tx = request.data.get('gateway_transaction_id')
        status_in = request.data.get('status')
        if status_in not in ('completed','failed','cancelled'):
            return Response({'detail': 'invalid status'}, status=status.HTTP_400_BAD_REQUEST)
        payment.gateway_transaction_id = gateway_tx
        payment.status = status_in
        payment.save()
        return Response({'ok': True})


class WebhookReceiver(APIView):
    permission_classes = []  # at minimum validate signature

    def post(self, request):
        """Generic webhook endpoint for payment gateway callbacks.
        You must verify signature from gateway using a shared secret and then map the gateway payload to Payment.
        """
        # Example: assume gateway sends {"order_id":..., "tx_id":..., "status": "success"}
        payload = request.data
        # TODO: verify signature/hmac using headers and settings.PAYMENT_GATEWAY_SECRET
        order_id = payload.get('order_id')
        tx_id = payload.get('tx_id')
        status_map = {'success': 'completed', 'failed': 'failed', 'cancelled': 'cancelled'}
        status_in = status_map.get(payload.get('status'))
        if not order_id or not tx_id or not status_in:
            return Response({'detail': 'invalid payload'}, status=status.HTTP_400_BAD_REQUEST)
        # Find payment by order_id (you can store gateway id too)
        try:
            p = Payment.objects.get(order_id=order_id)
        except Payment.DoesNotExist:
            return Response({'detail': 'payment not found'}, status=status.HTTP_404_NOT_FOUND)
        # idempotency: ignore if already completed
        if p.status == 'completed':
            return Response({'ok': True})
        p.gateway_transaction_id = tx_id
        p.status = status_in
        p.save()
        return Response({'ok': True})


class RefundViewSet(viewsets.ModelViewSet):
    queryset = Refund.objects.all()
    serializer_class = RefundSerializer

    def create(self, request, *args, **kwargs):
        # Create refund record and optionally call gateway API to process refund
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        refund = serializer.save(status='pending')
        # Optionally: schedule refund processing via Celery
        try:
            from .tasks import process_refund
            process_refund.delay(refund.id)
        except Exception:
            # if Celery not configured, try synchronous minimal handling
            refund.status = 'failed'
            refund.save()
        return Response(self.get_serializer(refund).data, status=status.HTTP_201_CREATED)

