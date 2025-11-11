from jose import jwt, JWTError
from django.conf import settings

SECRET_KEY = settings.JWT_SECRET_KEY  # must be the SAME as Auth Service
ALGORITHM = settings.JWT_ALGORITHM

def verify_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None
