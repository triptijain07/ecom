# apigateway/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('Gateway.urls')),  # All API requests go through gateway
]
