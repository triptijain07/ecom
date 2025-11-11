from django.contrib import admin
from .models import ShopAccount, Payment, Refund


@admin.register(ShopAccount)
class ShopAccountAdmin(admin.ModelAdmin):
 list_display = ('shop_id', 'display_name', 'active', 'created_at')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id','order_id','shop_id','amount','status','created_at')
    search_fields = ('order_id','gateway_transaction_id')


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ('id','payment','amount','status','created_at')