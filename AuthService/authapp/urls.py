from django.urls import path
from .views import (
    CustomerRegisterView, ShopOwnerRegisterView, LoginView, LogoutView,
    UserInfoView, TokenVerifyView
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('register/customer/', CustomerRegisterView.as_view(), name='customer_register'),
    path('register/shop_owner/', ShopOwnerRegisterView.as_view(), name='shop_owner_register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('user/info/', UserInfoView.as_view(), name='user_info'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
]
