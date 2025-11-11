# shop_service/urls.py (main project urls.py excerpt)
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('shops.urls')),  # Mount the shops API under /api/
]