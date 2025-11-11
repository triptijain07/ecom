from rest_framework import permissions
from django.conf import settings
import requests
from rest_framework.exceptions import PermissionDenied

SHOP_SERVICE_URL = getattr(settings, "SHOP_SERVICE_URL", "http://127.0.0.1:8001/api/v1/shops/")

def _fetch_shop(shop_id, token=None):
    """Helper to fetch shop info from ShopService. Returns dict or raises PermissionDenied."""
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        r = requests.get(f"{SHOP_SERVICE_URL}{shop_id}/", headers=headers, timeout=5)
        if r.status_code == 200:
            return r.json()
        if r.status_code == 404:
            return None
        raise PermissionDenied("Could not fetch shop from ShopService")
    except requests.RequestException:
        raise PermissionDenied("ShopService unavailable")

class IsShopOwnerOrReadOnly(permissions.BasePermission):
    """
    Allow full write access only to shop owners. Read is allowed for all safe methods.
    Expects authentication to set request.user with `.id` and `.role` (your SimpleUser).
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if not getattr(request, "user", None) or not request.user.is_authenticated:
            return False
        return request.user.role == "shop_owner"

    def has_object_permission(self, request, view, obj):
        # For object-level checks, ensure the requester owns the shop
        if request.method in permissions.SAFE_METHODS:
            return True
        if not getattr(request, "user", None) or not request.user.is_authenticated:
            return False
        if request.user.role != "shop_owner":
            return False
        # Best-effort check: either JWT contains shop_ids or call ShopService to verify ownership
        token = getattr(request, "auth", None)
        token_shop_ids = getattr(request.user, "shop_ids", None) or None
        if token_shop_ids:
            if isinstance(token_shop_ids, int):
                token_shop_ids = [token_shop_ids]
            return int(obj.shop_id) in [int(s) for s in token_shop_ids]
        # fallback: query ShopService
        shop = _fetch_shop(obj.shop_id, token=token)
        if not shop:
            return False
        owner_id = shop.get("owner_id")
        return int(owner_id) == int(request.user.id)
