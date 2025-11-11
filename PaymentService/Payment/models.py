from django.db import models
from django.utils import timezone

class ShopAccount(models.Model):
    """Represents the payment information for a shop (account details or QR payload)."""
    shop_id = models.IntegerField(unique=True)
    display_name = models.CharField(max_length=255)
    account_details = models.JSONField(blank=True, null=True) # e.g. {"upi": "shop@bank", "bank": {...}}
    qr_payload = models.TextField(blank=True, null=True) # raw QR string (e.g. UPI deep link)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return f"ShopAccount(shop={self.shop_id}, active={self.active})"




class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('initiated', 'Initiated'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]


    id = models.BigAutoField(primary_key=True)
    order_id = models.CharField(max_length=128, db_index=True)
    shop_id = models.IntegerField(db_index=True)
    customer_id = models.IntegerField(null=True, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, default='INR')
    gateway = models.CharField(max_length=64, blank=True, null=True)
    gateway_transaction_id = models.CharField(max_length=256, blank=True, null=True, unique=True)
    status = models.CharField(max_length=20, choices= STATUS_CHOICES, default='pending')
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    idempotency_key = models.CharField(max_length=128, blank=True, null=True, db_index=True)


class Meta:
    indexes = [
    models.Index(fields=['shop_id', 'created_at']),
    ]


def __str__(self):
    return f"Payment(order={self.order_id}, amount={self.amount}, status={self.status})"




class Refund(models.Model):
    id = models.BigAutoField(primary_key=True)
    payment = models.ForeignKey(Payment, related_name='refunds', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField(blank=True, null=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=[('pending','Pending'), ('processed','Processed'), ('failed','Failed')], default='pending')
    gateway_refund_id = models.CharField(max_length=256, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"Refund(payment={self.payment.id}, amount={self.amount}, status={self.status})"