from rest_framework import serializers
from .models import ShopAccount, Payment, Refund


class ShopAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopAccount
        fields = '__all__'




class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        read_only_fields = ('status', 'gateway_transaction_id', 'created_at', 'updated_at')
        fields = '__all__'


    def validate(self, data):
        # Basic validation: amount positive, shop active
        if data.get('amount') is None or data['amount'] <= 0:
            raise serializers.ValidationError({'amount': 'Amount must be > 0'})
        # Check shop exists and active
        from .models import ShopAccount
        try:
            sa = ShopAccount.objects.get(shop_id=data['shop_id'], active=True)
        except ShopAccount.DoesNotExist:
            raise serializers.ValidationError({'shop_id': 'Shop payment details not found or inactive'})
        return data




class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = '__all__'
        read_only_fields = ('status', 'processed_at', 'gateway_refund_id', 'created_at')


    def validate(self, data):
    # ensure refund amount <= payment amount - already refunded
        payment = data['payment']
        total_refunded = sum([r.amount for r in payment.refunds.all()])
        if data['amount'] + total_refunded > payment.amount:
            raise serializers.ValidationError({'amount': 'Refund exceeds paid amount'})
        return data