from rest_framework import serializers
from .models import Inventory
from django.conf import settings
import requests

PRODUCT_SERVICE_URL = getattr(settings, "PRODUCT_SERVICE_URL", "http://127.0.0.1:8000/api/v1/products/")

class InventorySerializer(serializers.ModelSerializer):
    available = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Inventory
        fields = ("id", "product_id", "shop_id", "stock", "reserved", "threshold", "available", "meta", "updated_at")
        read_only_fields = ("id", "reserved", "available", "updated_at")

    def get_available(self, obj):
        return obj.available()

    def validate_product_id(self, value):
        """
        Optional: verify product exists in ProductService.
        If ProductService is not available or you prefer not to validate, remove this.
        """
        # Only attempt validation if configured to do so
        validate = getattr(settings, "INVENTORY_VALIDATE_PRODUCT", True)
        if not validate:
            return value

        try:
            r = requests.get(f"{PRODUCT_SERVICE_URL}{value}/", timeout=5)
            if r.status_code != 200:
                raise serializers.ValidationError(f"Product {value} not found in ProductService")
        except requests.RequestException:
            # If ProductService unavailable, fail-safe: allow create but warn developer
            # You can choose to raise ValidationError instead
            raise serializers.ValidationError("Could not validate product with ProductService (unavailable)")
        return value

    def create(self, validated_data):
        # create or update existing record with unique (product_id, shop_id)
        obj, created = Inventory.objects.update_or_create(
            product_id=validated_data["product_id"],
            shop_id=validated_data["shop_id"],
            defaults={
                "stock": validated_data.get("stock", 0),
                "threshold": validated_data.get("threshold", 0),
                "meta": validated_data.get("meta", {}),
            },
        )
        return obj
