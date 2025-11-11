from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ShopAccountViewSet, PaymentViewSet, RefundViewSet, WebhookReceiver


router = DefaultRouter()
router.register(r'shop_accounts', ShopAccountViewSet, basename='shopaccount')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'refunds', RefundViewSet, basename='refund')


urlpatterns = [
path('', include(router.urls)),
path('webhook/', WebhookReceiver.as_view(), name='payment-webhook'),
]