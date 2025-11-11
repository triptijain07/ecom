# order/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from rest_framework.exceptions import PermissionDenied, NotFound, ValidationError
from django.shortcuts import get_object_or_404
from django.conf import settings
from .models import Order, OrderItem
from .serializers import OrderSerializer, OrderItemSerializer
from .permissions import IsShopForOrder
import requests
from decimal import Decimal
from datetime import datetime

# endpoints (adjust hosts/ports if needed)
SHOP_SERVICE_URL = getattr(settings, "SHOP_SERVICE_URL", "http://127.0.0.1:8001/api/shops/")
PRODUCT_SERVICE_URL = getattr(settings, "PRODUCT_SERVICE_URL", "http://127.0.0.1:8000/api/v1/products/")

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().order_by("-created_at")
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def list(self, request, *args, **kwargs):
        """
        Customers see their own orders,
        Shop owners see orders of their shops.
        """
        if not request.user or not request.user.is_authenticated:
            return Response([], status=status.HTTP_200_OK)

        if request.user.role == "customer":
            qs = Order.objects.filter(customer_id=request.user.id)
        elif request.user.role == "shop_owner":
            # fetch shops owned by this user
            resp = requests.get(f"{SHOP_SERVICE_URL}?owner_id={request.user.id}")
            if resp.status_code == 200:
                shop_ids = [s["id"] for s in resp.json().get("results", [])]
                qs = Order.objects.filter(shop_id__in=shop_ids)
            else:
                qs = Order.objects.none()
        else:
            qs = Order.objects.none()

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = OrderSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(OrderSerializer(qs, many=True).data)

    # ---------------- CART ----------------
    @action(detail=False, methods=["post"], url_path="cart/create")
    def cart_create(self, request):
        if request.user.role != "customer":
            raise PermissionDenied("Only customers can create carts")

        shop_id = request.data.get("shop_id")
        if not shop_id:
            raise ValidationError({"shop_id": "required"})

        existing = Order.objects.filter(
            customer_id=request.user.id, shop_id=shop_id, status="cart"
        ).first()
        if existing:
            return Response(OrderSerializer(existing).data)

        order = Order.objects.create(
            customer_id=request.user.id, shop_id=shop_id, status="cart"
        )
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="cart/add-item")
    def cart_add_item(self, request, pk=None):
        order = get_object_or_404(Order, pk=pk)

        if request.user.role != "customer" or order.customer_id != request.user.id:
            raise PermissionDenied("Only cart owner can add items")
        if order.status != "cart":
            raise ValidationError("Order is not a cart")

        product_id = request.data.get("product_id")
        quantity = int(request.data.get("quantity", 1))
        if not product_id:
            raise ValidationError({"product_id": "required"})

        # validate product
        prod_resp = requests.get(f"{PRODUCT_SERVICE_URL}{product_id}/")
        if prod_resp.status_code != 200:
            raise ValidationError({"product": "Product not found"})
        prod = prod_resp.json()

        item = OrderItem.objects.filter(order=order, product_id=product_id).first()
        price = Decimal(str(prod.get("price", "0")))

        if item:
            item.quantity += quantity
            item.price = price
            item.save()
        else:
            OrderItem.objects.create(
                order=order,
                product_id=product_id,
                product_name=prod.get("name", ""),
                quantity=quantity,
                price=price,
            )

        order.total_amount = sum(i.price * i.quantity for i in order.items.all())
        order.save()
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=["post"], url_path="cart/remove-item")
    def cart_remove_item(self, request, pk=None):
        order = get_object_or_404(Order, pk=pk)

        if request.user.role != "customer" or order.customer_id != request.user.id:
            raise PermissionDenied("Only cart owner can remove items")
        if order.status != "cart":
            raise ValidationError("Order is not a cart")

        product_id = request.data.get("product_id")
        if not product_id:
            raise ValidationError({"product_id": "required"})

        item = OrderItem.objects.filter(order=order, product_id=product_id).first()
        if not item:
            raise NotFound("Item not found in cart")
        item.delete()

        order.total_amount = sum(i.price * i.quantity for i in order.items.all())
        order.save()
        return Response(OrderSerializer(order).data)

    # ---------------- CHECKOUT ----------------
    @action(detail=True, methods=["post"], url_path="checkout")
    def checkout(self, request, pk=None):
        order = get_object_or_404(Order, pk=pk)

        if request.user.role != "customer" or order.customer_id != request.user.id:
            raise PermissionDenied("Only cart owner can checkout")
        if order.status != "cart":
            raise ValidationError("Order is not in cart status")

        fulfilment = request.data.get("fulfilment")
        if fulfilment not in ("pickup", "delivery"):
            raise ValidationError({"fulfilment": "must be pickup or delivery"})

        if fulfilment == "delivery":
            shop_resp = requests.get(f"{SHOP_SERVICE_URL}{order.shop_id}/")
            if shop_resp.status_code != 200:
                raise ValidationError("Shop not found")
            shop = shop_resp.json()
            if not shop.get("delivery_enabled"):
                raise ValidationError("Delivery not available for this shop")

            address = request.data.get("address")
            if not address:
                raise ValidationError({"address": "required for delivery"})

            order.address = address
            order.fulfilment = "delivery"
            order.status = "pending"

        else:  # pickup
            order.fulfilment = "pickup"
            pickup_time = request.data.get("pickup_time")
            if pickup_time:
                try:
                    order.pickup_time = datetime.fromisoformat(pickup_time)
                except Exception:
                    raise ValidationError({"pickup_time": "invalid ISO datetime"})
            order.status = "pending"

        order.save()
        self.notify_shop_new_order(order)
        return Response(OrderSerializer(order).data)

    # ---------------- SHOP OWNER ACTIONS ----------------
    @action(detail=True, methods=["post"], url_path="shop/accept", permission_classes=[IsShopForOrder])
    def shop_accept(self, request, pk=None):
        order = get_object_or_404(Order, pk=pk)
        if order.status != "pending":
            raise ValidationError("Order not in pending")
        order.status = "accepted"
        order.save()
        self.notify_customer(order, "accepted")
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=["post"], url_path="shop/mark-ready", permission_classes=[IsShopForOrder])
    def shop_mark_ready(self, request, pk=None):
        order = get_object_or_404(Order, pk=pk)
        order.status = "ready_for_pickup" if order.fulfilment == "pickup" else "preparing"
        order.save()
        self.notify_customer(order, "ready")
        return Response(OrderSerializer(order).data)

    @action(detail=True, methods=["post"], url_path="shop/complete", permission_classes=[IsShopForOrder])
    def shop_complete(self, request, pk=None):
        order = get_object_or_404(Order, pk=pk)
        order.status = "delivered" if order.fulfilment == "delivery" else "completed"
        order.save()
        self.notify_customer(order, "completed")
        return Response(OrderSerializer(order).data)

    # ---------------- NOTIFICATIONS ----------------
    def notify_shop_new_order(self, order):
        # TODO: implement webhook/celery
        pass

    def notify_customer(self, order, event):
        # TODO: implement webhook/push/email
        pass
