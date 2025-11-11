# order/permissions.py
from rest_framework import permissions

class IsCustomerOrReadOnly(permissions.BasePermission):
    # allow safe methods to everyone; write only to authenticated customers
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        # expect request.user to be JWT payload dict
        user = getattr(request, "user", None)
        if not user or not isinstance(user, dict):
            return False
        return user.get("role") == "customer" or user.get("role") == "shop_owner"  # shop_owner may create orders too

class IsShopForOrder(permissions.BasePermission):
    """
    Allow shop staff to manage/advance orders for their shop only.
    """
    def has_object_permission(self, request, view, obj):
        user = getattr(request, "user", None)
        if not user or not isinstance(user, dict):
            return False
        # shop staff have role shop_owner and must own obj.shop_id (validation via shop service would be safer)
        if user.get("role") != "shop_owner":
            return False
        # If JWT contains shop_ids, check
        shop_ids = user.get("shop_ids") or []
        if isinstance(shop_ids, int):
            shop_ids = [shop_ids]
        return int(obj.shop_id) in [int(s) for s in shop_ids]
