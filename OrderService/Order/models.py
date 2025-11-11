# order/models.py
from django.db import models
from django.utils import timezone
from django.contrib.postgres.fields import JSONField  # if using Postgres; in Django 4+ JSONField exists in core

class Order(models.Model):
    # Basic order metadata
    STATUS_CHOICES = [
        ("cart", "Cart"),              # customer is still building cart
        ("pending", "Pending"),        # checkout done, awaiting shop accept
        ("accepted", "Accepted"),      # shop accepted
        ("preparing", "Preparing"),    # shop preparing items
        ("ready_for_pickup", "Ready for pickup"),
        ("out_for_delivery", "Out for delivery"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
        ("failed", "Failed"),
    ]

    FULFILMENT_CHOICES = [
        ("pickup", "Pickup"),
        ("delivery", "Delivery"),
    ]

    id = models.BigAutoField(primary_key=True)
    customer_id = models.IntegerField(db_index=True)  # from AuthService
    shop_id = models.IntegerField(db_index=True)      # from ShopService
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="cart")
    fulfilment = models.CharField(max_length=20, choices=FULFILMENT_CHOICES, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default="INR")
    address = models.JSONField(null=True, blank=True)   # delivery address when fulfilment=delivery
    pickup_time = models.DateTimeField(null=True, blank=True)  # optional requested pickup time
    meta = models.JSONField(default=dict, blank=True)   # extensible metadata
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.id} shop={self.shop_id} cust={self.customer_id} status={self.status}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    product_id = models.IntegerField()         # product id from ProductService
    product_name = models.CharField(max_length=255)  # snapshot
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=12, decimal_places=2)  # price per unit snapshot
    meta = models.JSONField(default=dict, blank=True)  # e.g. variant options, weights
    created_at = models.DateTimeField(default=timezone.now)

    def line_total(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.product_name} x {self.quantity} (order {self.order_id})"
