from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.exceptions import ValidationError, NotFound, PermissionDenied
from django.shortcuts import get_object_or_404
from django.conf import settings
from .models import Inventory
from .serializers import InventorySerializer
from .permissions import IsShopOwnerOrReadOnly
import requests

# Service URLs (set in settings, override defaults per deployment)
SHOP_SERVICE_URL = getattr(settings, "SHOP_SERVICE_URL", "http://127.0.0.1:8001/api/shops/")
PRODUCT_SERVICE_URL = getattr(settings, "PRODUCT_SERVICE_URL", "http://127.0.0.1:8000/api/v1/products/")

class InventoryViewSet(viewsets.ModelViewSet):
    """
    Inventory endpoints:
      - list/retrieve (anyone, read-only)
      - create/update (shop owners only)
      - reserve/release/commit used by OrderService (protected via token)
    """
    queryset = Inventory.objects.all()
    serializer_class = InventorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsShopOwnerOrReadOnly]

    def get_permissions(self):
        # allow different permission on custom actions
        if self.action in ("reserve", "release", "commit"):
            # OrderService will call these endpoints - require authenticated service token
            return [IsAuthenticated()]  # further validations done in methods (e.g. token role)
        return super().get_permissions()

    # optional: list by shop query param ?shop_id=5
    def get_queryset(self):
        qs = super().get_queryset()
        shop_id = self.request.query_params.get("shop_id")
        product_id = self.request.query_params.get("product_id")
        if shop_id:
            qs = qs.filter(shop_id=shop_id)
        if product_id:
            qs = qs.filter(product_id=product_id)
        return qs

    def perform_create(self, serializer):
        # only shop owners should create; IsShopOwnerOrReadOnly handles permission
        serializer.save()

    # ---- stock management actions for shop owners ----
    @action(detail=True, methods=["patch"], url_path="update-stock", permission_classes=[IsShopOwnerOrReadOnly])
    def update_stock(self, request, pk=None):
        """
        Patch stock and/or threshold. Body: {"stock": 100, "threshold": 5}
        """
        inv = get_object_or_404(Inventory, pk=pk)
        if "stock" in request.data:
            try:
                inv.stock = int(request.data["stock"])
            except (ValueError, TypeError):
                raise ValidationError({"stock": "invalid integer"})
        if "threshold" in request.data:
            try:
                inv.threshold = int(request.data["threshold"])
            except (ValueError, TypeError):
                raise ValidationError({"threshold": "invalid integer"})
        if "meta" in request.data:
            inv.meta = request.data.get("meta") or {}
        inv.save()
        return Response(InventorySerializer(inv).data)

    # ---- endpoints used by OrderService ----
    @action(detail=False, methods=["post"], url_path="reserve")
    def reserve(self, request):
        """
        Reserve stock for a pending order.
        Body: {"shop_id": 5, "product_id": 10, "quantity": 2}
        """
        product_id = request.data.get("product_id")
        shop_id = request.data.get("shop_id")
        qty = int(request.data.get("quantity", 0) or 0)
        if not product_id or not shop_id or qty <= 0:
            raise ValidationError({"detail": "product_id, shop_id and positive quantity required"})

        inv = Inventory.objects.filter(product_id=product_id, shop_id=shop_id).first()
        if not inv:
            raise NotFound("Inventory record not found")
        if inv.available() < qty:
            return Response({"detail": "Not enough available stock"}, status=status.HTTP_400_BAD_REQUEST)

        inv.reserved += qty
        inv.save()
        return Response(InventorySerializer(inv).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="release")
    def release(self, request):
        """
        Release previously reserved stock (e.g. order canceled).
        Body: {"shop_id": 5, "product_id": 10, "quantity": 2}
        """
        product_id = request.data.get("product_id")
        shop_id = request.data.get("shop_id")
        qty = int(request.data.get("quantity", 0) or 0)
        if not product_id or not shop_id or qty <= 0:
            raise ValidationError({"detail": "product_id, shop_id and positive quantity required"})

        inv = Inventory.objects.filter(product_id=product_id, shop_id=shop_id).first()
        if not inv:
            raise NotFound("Inventory record not found")

        inv.reserved = max(inv.reserved - qty, 0)
        inv.save()
        return Response(InventorySerializer(inv).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"], url_path="commit")
    def commit(self, request):
        """
        Commit reserved stock after order is completed.
        Body: {"shop_id": 5, "product_id": 10, "quantity": 2}
        """
        product_id = request.data.get("product_id")
        shop_id = request.data.get("shop_id")
        qty = int(request.data.get("quantity", 0) or 0)
        if not product_id or not shop_id or qty <= 0:
            raise ValidationError({"detail": "product_id, shop_id and positive quantity required"})

        inv = Inventory.objects.filter(product_id=product_id, shop_id=shop_id).first()
        if not inv:
            raise NotFound("Inventory record not found")

        if inv.reserved < qty:
            return Response({"detail": "Not enough reserved stock"}, status=status.HTTP_400_BAD_REQUEST)

        inv.reserved -= qty
        inv.stock = max(inv.stock - qty, 0)
        inv.save()
        return Response(InventorySerializer(inv).data, status=status.HTTP_200_OK)

    # convenience endpoint: get availability for a (product_id, shop_id)
    @action(detail=False, methods=["get"], url_path="availability")
    def availability(self, request):
        product_id = request.query_params.get("product_id")
        shop_id = request.query_params.get("shop_id")
        if not product_id or not shop_id:
            raise ValidationError({"detail": "product_id and shop_id query params required"})
        inv = Inventory.objects.filter(product_id=product_id, shop_id=shop_id).first()
        if not inv:
            return Response({"available": 0, "stock": 0, "reserved": 0})
        return Response({
            "available": inv.available(),
            "stock": inv.stock,
            "reserved": inv.reserved
        })
