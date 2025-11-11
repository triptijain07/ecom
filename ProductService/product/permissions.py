from rest_framework import permissions

class IsShopOwner(permissions.BasePermission):
    """
    Allow access only to users with role 'shop_owner' based on JWT payload.
    Assumes JWTAuthentication sets request.user = payload dict from Auth Service.
    """

    def has_permission(self, request, view):
        user_payload = getattr(request, "user", None)  # decoded JWT payload
        if not user_payload or not isinstance(user_payload, dict):
            return False
        return user_payload.get("role") == "shop_owner"


class IsShopOwnerOfProduct(permissions.BasePermission):
    """
    Allow object-level operations only if product.shop_id matches the shop owner id from JWT payload.
    """

    def has_object_permission(self, request, view, obj):
        user_payload = getattr(request, "user", None)
        if not user_payload or not isinstance(user_payload, dict):
            return False
        # The JWT payload should contain user_id and optionally shop_ids
        token_user_id = user_payload.get("user_id")
        token_shop_ids = user_payload.get("shop_ids")
        # If shop_ids present, check if product.shop_id is in the list
        if token_shop_ids:
            if isinstance(token_shop_ids, int):
                token_shop_ids = [token_shop_ids]
            return int(obj.shop_id) in [int(s) for s in token_shop_ids]
        # Fallback: compare with user_id
        return int(obj.shop_id) == int(token_user_id)
