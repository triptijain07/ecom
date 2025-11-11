from celery import shared_task
from django.utils import timezone
from django.conf import settings

from .models import Refund, Payment

@shared_task(bind=True)
def process_refund(self, refund_id):
    refund = Refund.objects.get(pk=refund_id)
    payment = refund.payment
    # Example: call your gateway refund API
    # Here we'll mark processed for demo
    try:
        # gateway_resp = call_gateway_refund(payment.gateway_transaction_id, refund.amount)
        # if gateway_resp['status'] == 'ok':
        refund.status = 'processed'
        refund.processed_at = timezone.now()
        refund.gateway_refund_id = f"r-{refund.id}-{int(timezone.now().timestamp())}"
        refund.save()
        # mark payment as refunded if total refunded == payment.amount
        total_refunded = sum([r.amount for r in payment.refunds.all() if r.status == 'processed'])
        if total_refunded >= payment.amount:
            payment.status = 'refunded'
            payment.save()
    except Exception as e:
        refund.status = 'failed'
        refund.save()
        raise
