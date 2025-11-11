# shops/serializers.py
from rest_framework import serializers
from .models import Shop

class ShopSerializer(serializers.ModelSerializer):
    distance_km = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Shop
        fields = ['id', 'name', 'address', 'latitude', 'longitude', 'owner_id', 'distance_km']
        read_only_fields = ['owner_id', 'distance_km']  # 👈 owner_id is auto-filled

    def get_distance_km(self, obj):
        if hasattr(obj, "distance_km"):
            return obj.distance_km
        return None
