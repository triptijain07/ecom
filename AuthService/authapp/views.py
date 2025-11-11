from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from .serializers import CustomerRegisterSerializer, ShopOwnerRegisterSerializer, LoginSerializer, UserInfoSerializer
from .permissions import IsCustomer, IsShopOwner
from rest_framework.permissions import IsAuthenticated
from authapp.models import CustomUser



class CustomerRegisterView(APIView):
    permission_classes = []
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
    permission_classes = []
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

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from .jwt_utils import create_access_token, create_refresh_token

class LoginView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(username=username, password=password)
        if not user:
            return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

        payload = {"user_id": user.id, "role": user.role}
        access = create_access_token(payload)
        refresh = create_refresh_token(payload)

        return Response({
            "access": access,
            "refresh": refresh,
            "user_id": user.id,
            "role": user.role
        })

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

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .jwt_utils import verify_access_token

class TokenVerifyView(APIView):
    permission_classes = []
    authentication_classes = []

    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"error": "Token is required"}, status=status.HTTP_400_BAD_REQUEST)

        payload = verify_access_token(token)
        if not payload:
            return Response({"error": "Invalid or expired token"}, status=status.HTTP_401_UNAUTHORIZED)

        return Response({
            "user_id": payload["user_id"],
            "role": payload["role"]
        })
