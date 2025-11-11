from rest_framework import serializers
from .models import Product, ProductImage, Category
from django.conf import settings

class ProductImageSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ("id", "image", "alt_text")

    def get_image(self, obj):
        request = self.context.get('request')
        if obj.image and hasattr(obj.image, 'url'):
            # Return full URL if request is available
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return None

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ("id", "name", "slug")

class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = (
            "id", "sku", "name", "description", "price", "category",
            "available", "shop_id", "shop_name", "shop_lat", "shop_lng",
            "tags", "images", "created_at", "updated_at"
        )
        read_only_fields = ("shop_id", "shop_name", "shop_lat", "shop_lng", "created_at", "updated_at")
