from rest_framework import authentication, exceptions
from django.conf import settings
from jose import jwt, JWTError

SECRET_KEY = settings.JWT_SECRET_KEY  # must match Auth Service
ALGORITHM = settings.JWT_ALGORITHM

class JWTAuthentication(authentication.BaseAuthentication):
    """
    Custom JWT authentication for Product Service.
    Decodes token issued by Auth Service.
    Sets `request.user` as payload dictionary.
    """

    def authenticate(self, request):
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None  # allows other auth classes / anonymous access

        # Expecting header: "Bearer <token>"
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise exceptions.AuthenticationFailed("Invalid Authorization header format.")

        token = parts[1]

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError:
            raise exceptions.AuthenticationFailed("Invalid or expired token.")

        # Optional: check token type
        if payload.get("type") and payload["type"] != "access":
            raise exceptions.AuthenticationFailed("Token is not an access token.")

        # Return payload as "user" and token as "auth"
        return (payload, token)
