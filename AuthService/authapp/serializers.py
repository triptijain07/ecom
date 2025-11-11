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