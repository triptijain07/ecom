from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from django.conf import settings
import jwt


class SimpleUser:
    """
    Lightweight user object that only carries the ID from JWT.
    Prevents hitting auth_user table.
    """
    def __init__(self, user_id):
        self.id = user_id

    @property
    def is_authenticated(self):
        return True


class JWTAuthentication(BaseAuthentication):
    """
    Authenticate using JWT token from Authorization header.
    """
    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token = auth_header.split(" ")[1]

        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed("Token has expired")
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed("Invalid or malformed token")

        user_id = payload.get("user_id")
        if not user_id:
            raise exceptions.AuthenticationFailed("Invalid token payload: no user_id")

        # Instead of querying auth_user, just return SimpleUser
        return (SimpleUser(user_id), None)
