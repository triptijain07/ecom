# Auth-Service

# Authentication Microservice for Ecommerce Platform

This is a standalone Django-based authentication microservice using DRF and SimpleJWT.
It handles user registration, login, logout, and token validation for customers and shop owners.
Designed to integrate with an API gateway and other microservices (e.g., product, order, inventory).
Exposes RESTful endpoints for authentication and user info, with role-based access control.

# 1. Install required packages (run in terminal):
pip install django djangorestframework djangorestframework-simplejwt psycopg2-binary

# 2. Project structure:
 auth_service/
 ├── auth_service/
 │   ├── __init__.py
 │   ├── settings.py
 │   ├── urls.py
 ├── authapp/
 │   ├── __init__.py
 │   ├── models.py
 │   ├── serializers.py
 │   ├── views.py
 │   ├── urls.py
 │   ├── permissions.py
 └── manage.py

# 3. Update settings.py
INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'rest_framework',
    'rest_framework_simplejwt',
    'authapp',
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
}

from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'USER_ID_FIELD': 'id',
    'USER_ID_CLAIM': 'user_id',
}

AUTH_USER_MODEL = 'authapp.CustomUser'

# Database configuration (e.g., PostgreSQL)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'auth_db',
        'USER': 'auth_user',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# 4. authapp/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('customer', 'Customer'),
        ('shop_owner', 'Shop Owner'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)  # For customer location
    longitude = models.FloatField(blank=True, null=True)

# 5. authapp/serializers.py
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import CustomUser

class BaseRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

class CustomerRegisterSerializer(BaseRegisterSerializer):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password', 'password2', 'phone_number', 'address', 'latitude', 'longitude')

    def validate(self, attrs):
        attrs = super().validate(attrs)
        attrs['role'] = 'customer'
        return attrs

    def create(self, validated_data):
        user = CustomUser.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            role=validated_data['role'],
            phone_number=validated_data.get('phone_number', ''),
            address=validated_data.get('address', ''),
            latitude=validated_data.get('latitude'),
            longitude=validated_data.get('longitude'),
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

class ShopOwnerRegisterSerializer(BaseRegisterSerializer):
    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password', 'password2', 'phone_number', 'address')

    def validate(self, attrs):
        attrs = super().validate(attrs)
        attrs['role'] = 'shop_owner'
        return attrs

    def create(self, validated_data):
        user = CustomUser.objects.create(
            username=validated_data['username'],
            email=validated_data['email'],
            role=validated_data['role'],
            phone_number=validated_data.get('phone_number', ''),
            address=validated_data.get('address', ''),
        )
        user.set_password(validated_data['password'])
        user.save()
        # Notify shop service to create shop profile (e.g., via message queue or API call)
        return user

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

class UserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'role', 'phone_number', 'address', 'latitude', 'longitude')

# 6. authapp/permissions.py
from rest_framework.permissions import BasePermission

class IsCustomer(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'customer'

class IsShopOwner(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'shop_owner'

# 7. authapp/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import CustomerRegisterSerializer, ShopOwnerRegisterSerializer, LoginSerializer, UserInfoSerializer
from .permissions import IsCustomer, IsShopOwner

class CustomerRegisterView(APIView):
    def post(self, request):
        serializer = CustomerRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "message": "Customer registered successfully",
                "user_id": user.id,
                "role": user.role
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ShopOwnerRegisterView(APIView):
    def post(self, request):
        serializer = ShopOwnerRegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({
                "message": "Shop Owner registered successfully",
                "user_id": user.id,
                "role": user.role
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = authenticate(
                username=serializer.validated_data['username'],
                password=serializer.validated_data['password']
            )
            if user:
                refresh = RefreshToken.for_user(user)
                return Response({
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'user_id': user.id,
                    'role': user.role,
                })
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh_token"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"message": "Successfully logged out"}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class UserInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserInfoSerializer(request.user)
        return Response(serializer.data)

class TokenVerifyView(APIView):
    def post(self, request):
        # For other microservices to verify tokens via API gateway
        token = request.data.get('token')
        try:
            access_token = RefreshToken(token)
            user_id = access_token['user_id']
            user = CustomUser.objects.get(id=user_id)
            return Response({
                'user_id': user.id,
                'role': user.role,
                'is_active': user.is_active
            })
        except Exception:
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_401_UNAUTHORIZED)

# 8. authapp/urls.py
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

# 9. auth_service/urls.py
from django.urls import path, include

urlpatterns = [
    path('api/auth/', include('authapp.urls')),
]

# 10. Dockerfile (for deployment)
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "auth_service.wsgi:application"]

# 11. requirements.txt
django==4.2.11
djangorestframework==3.15.1
djangorestframework-simplejwt==5.3.1
psycopg2-binary==2.9.9
gunicorn==22.0.0

# 12. Run migrations (in terminal):
python manage.py makemigrations
python manage.py migrate

# 13. Run the server (for development):
python manage.py runserver

# API Gateway Integration:
- Route requests to /api/auth/* to this service (e.g., http://auth-service:8000/api/auth/).
- Other microservices (product, order, etc.) call /api/auth/token/verify/ to validate tokens.
- Customer website (e.g., customer.example.com) and shop owner website (e.g., shopowner.example.com)
  send auth requests via the API gateway.

# Endpoints (accessed via API gateway, e.g., /api/auth/register/customer/):
- POST /api/auth/register/customer/
   Body: {"username": "customer1", "email": "cust@example.com", "password": "pass123", "password2": "pass123", "phone_number": "1234567890", "address": "123 Street", "latitude": 37.7749, "longitude": -122.4194}
- POST /api/auth/register/shop_owner/
   Body: {"username": "owner1", "email": "owner@example.com", "password": "pass123", "password2": "pass123", "phone_number": "0987654321", "address": "456 Avenue"}
- POST /api/auth/login/
   Body: {"username": "customer1", "password": "pass123"}
- POST /api/auth/logout/
   Body: {"refresh_token": "<refresh_token>"}
- POST /api/auth/token/refresh/
   Body: {"refresh": "<refresh_token>"}
- GET /api/auth/user/info/
   Header: Authorization: Bearer <access_token>
- POST /api/auth/token/verify/
   Body: {"token": "<access_token>"}

# Notes:
 - Shop creation: Handled by a separate shop service. After shop owner registration, send a message (e.g., via Kafka/RabbitMQ) to the shop service to create a shop profile.
 - Other microservices: Product exploration, AI search, inventory, and delivery partnerships are handled by separate services, which use /api/auth/token/verify/ to check user roles and permissions.
 - API Gateway: Configure to forward auth requests to this service and validate tokens for other services.
 - Scalability: Deploy with Docker, use a load balancer, and scale horizontally. Store tokens in Redis for blacklisting if needed.
 - Security: Use HTTPS, rate limiting in the API gateway, and secure JWT signing keys.
