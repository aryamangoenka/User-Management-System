"""
Django-FastAPI Authentication Integration
Allows FastAPI to authenticate users from Django's authentication system
"""

import os
import sys
import django
from typing import Optional, Dict, Any
import jwt
from datetime import datetime, timedelta

# Add Django project to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'user_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token

User = get_user_model()


class DjangoFastAPIBridge:
    """Bridge between Django and FastAPI authentication systems"""
    
    def __init__(self):
        self.secret_key = self._get_django_secret_key()
    
    def _get_django_secret_key(self) -> str:
        """Get Django's secret key for JWT signing"""
        from django.conf import settings
        return settings.SECRET_KEY
    
    def validate_django_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Validate Django REST Framework token"""
        try:
            django_token = Token.objects.get(key=token)
            user = django_token.user
            
            if user.is_active:
                return {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "is_active": user.is_active,
                    "is_superuser": user.is_superuser,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "role": getattr(user, 'role', 'user'),
                    "created_at": user.date_joined.isoformat(),
                }
            return None
        except Token.DoesNotExist:
            return None
    
    def create_fastapi_token(self, django_user_data: Dict[str, Any]) -> str:
        """Create FastAPI JWT token from Django user data"""
        payload = {
            "sub": django_user_data["username"],
            "user_id": django_user_data["id"],
            "email": django_user_data["email"],
            "role": django_user_data.get("role", "user"),
            "is_superuser": django_user_data.get("is_superuser", False),
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow(),
            "source": "django"
        }
        
        from jose import jwt
        return jwt.encode(payload, self.secret_key, algorithm="HS256")
    
    def sync_user_to_fastapi(self, django_user_id: int) -> Optional[Dict[str, Any]]:
        """Sync Django user to FastAPI database"""
        try:
            user = User.objects.get(id=django_user_id)
            
            # This would sync to FastAPI database
            user_data = {
                "username": user.username,
                "email": user.email,
                "full_name": f"{user.first_name} {user.last_name}".strip(),
                "is_active": user.is_active,
                "is_superuser": user.is_superuser,
                "external_id": user.id,  # Reference to Django user
                "created_at": user.date_joined,
            }
            
            return user_data
        except User.DoesNotExist:
            return None
    
    def authenticate_cross_platform(self, token: str) -> Optional[Dict[str, Any]]:
        """Authenticate user across Django and FastAPI"""
        # Try Django token first
        user_data = self.validate_django_token(token)
        if user_data:
            return user_data
        
        # Try FastAPI JWT token
        try:
            from jose import jwt
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            
            # If it's a Django-sourced token, validate user still exists
            if payload.get("source") == "django":
                user_id = payload.get("user_id")
                if user_id:
                    try:
                        user = User.objects.get(id=user_id, is_active=True)
                        return {
                            "id": user.id,
                            "username": user.username,
                            "email": user.email,
                            "is_active": user.is_active,
                            "is_superuser": user.is_superuser,
                            "role": getattr(user, 'role', 'user'),
                        }
                    except User.DoesNotExist:
                        return None
            
            # Regular FastAPI token
            return {
                "username": payload.get("sub"),
                "user_id": payload.get("user_id"),
                "email": payload.get("email"),
                "is_active": True,
                "is_superuser": payload.get("is_superuser", False),
                "role": payload.get("role", "user"),
            }
            
        except Exception:
            return None


# Global bridge instance
auth_bridge = DjangoFastAPIBridge()


def get_django_user_from_token(token: str) -> Optional[Dict[str, Any]]:
    """Helper function to get Django user from token"""
    return auth_bridge.validate_django_token(token)


def create_unified_token(django_token: str) -> Optional[str]:
    """Create a unified token that works across both systems"""
    user_data = auth_bridge.validate_django_token(django_token)
    if user_data:
        return auth_bridge.create_fastapi_token(user_data)
    return None


def sync_user_from_django(user_id: int) -> Optional[Dict[str, Any]]:
    """Sync a Django user to FastAPI system"""
    return auth_bridge.sync_user_to_fastapi(user_id) 