from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import CustomUser

class UserSerializer(serializers.ModelSerializer):
    """Serializer for user objects"""
    user_id = serializers.IntegerField(source='id', read_only=True)
    user_name = serializers.CharField(source='username', read_only=True)
    phone = serializers.CharField(source='phone_number')
    create_at = serializers.DateTimeField(source='created_at', read_only=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    
    class Meta:
        model = CustomUser
        fields = (
            'user_id', 'user_name', 'username', 'email', 'first_name', 'last_name', 
            'phone', 'phone_number', 'address', 'role', 'is_active', 'last_login', 
            'create_at', 'created_at', 'date_joined', 'profile_picture'
        )
        read_only_fields = ('user_id', 'user_name', 'create_at', 'created_at', 'date_joined', 'last_login')

class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(write_only=True, min_length=8, style={'input_type': 'password'})
    password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})
    phone = serializers.CharField(source='phone_number', required=True)
    address = serializers.CharField(required=True)
    
    class Meta:
        model = CustomUser
        fields = (
            'username', 'email', 'first_name', 'last_name', 'phone', 
            'address', 'role', 'password', 'password_confirm'
        )

    def validate(self, attrs):
        """Validate that passwords match and meet Django's password requirements"""
        password = attrs.get('password')
        password_confirm = attrs.pop('password_confirm', None)
        
        if password != password_confirm:
            raise serializers.ValidationError("Passwords do not match.")
            
        # Validate password strength using Django's built-in validators
        try:
            validate_password(password)
        except ValidationError as e:
            raise serializers.ValidationError({'password': e.messages})
            
        return attrs

    def create(self, validated_data):
        """Create and return a new user with encrypted password"""
        return CustomUser.objects.create_user(**validated_data)

class UserDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for complete user information"""
    user_id = serializers.IntegerField(source='id', read_only=True)
    user_name = serializers.CharField(source='username')
    phone = serializers.CharField(source='phone_number')
    create_at = serializers.DateTimeField(source='created_at', read_only=True)
    profile_picture = serializers.ImageField(required=False, allow_null=True)
    
    class Meta:
        model = CustomUser
        fields = (
            'user_id', 'user_name', 'username', 'email', 'password', 'first_name', 
            'last_name', 'phone', 'role', 'is_active', 'last_login', 'create_at', 'profile_picture'
        )
        extra_kwargs = {
            'password': {'write_only': True},
        }
        read_only_fields = ('user_id', 'create_at', 'last_login')

class AuthTokenSerializer(serializers.Serializer):
    """Serializer for user authentication"""
    username = serializers.CharField()
    password = serializers.CharField(style={'input_type': 'password'}, trim_whitespace=False)

    def validate(self, attrs):
        """Validate and authenticate the user"""
        username = attrs.get('username')
        password = attrs.get('password')

        user = authenticate(
            request=self.context.get('request'),
            username=username,
            password=password
        )

        if not user:
            msg = 'Unable to authenticate with provided credentials'
            raise serializers.ValidationError(msg, code='authentication')

        attrs['user'] = user
        return attrs 