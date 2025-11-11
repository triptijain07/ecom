# order/serializers.py
from rest_framework import serializers
from .models import Order, OrderItem

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ("id", "product_id", "product_name", "quantity", "price", "meta", "created_at")
        read_only_fields = ("id", "product_name", "price", "created_at")

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, required=False)
    class Meta:
        model = Order
        fields = ("id", "customer_id", "shop_id", "status", "fulfilment", "total_amount",
                  "currency", "address", "pickup_time", "items", "meta", "created_at", "updated_at")
        read_only_fields = ("id", "status", "total_amount", "created_at", "updated_at")

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        order = Order.objects.create(**validated_data)
        total = 0
        for item in items_data:
            # item must contain product_id and quantity; product_name/price will be filled on add_item endpoint
            OrderItem.objects.create(order=order, **item)
            total += item.get("quantity", 1) * item.get("price", 0)
        order.total_amount = total
        order.save()
        return order
