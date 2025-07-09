from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from .models import CustomUser
from .serializers import UserSerializer, UserRegistrationSerializer, AuthTokenSerializer
from rest_framework.reverse import reverse
import logging

logger = logging.getLogger('accounts')

class UserListCreateAPIView(generics.ListCreateAPIView):
    """API view for listing and creating users"""
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        """Return appropriate serializer class"""
        if self.request.method == 'POST':
            return UserRegistrationSerializer
        return UserSerializer

class UserDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """API view for retrieving, updating and deleting a user"""
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register_api(request):
    """Register a new user via API"""
    logger.info(f"User registration attempt for username: {request.data.get('username', 'Unknown')}")
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        logger.info(f"User {user.username} registered successfully")
        return Response({
            'user': UserSerializer(user).data,
            'token': token.key,
            'message': 'User registered successfully'
        }, status=status.HTTP_201_CREATED)
    logger.warning(f"User registration failed for username: {request.data.get('username', 'Unknown')} - Errors: {serializer.errors}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_api(request):
    """Login user via API"""
    username = request.data.get('username', 'Unknown')
    logger.info(f"Login attempt for username: {username}")
    serializer = AuthTokenSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        logger.info(f"User {user.username} logged in successfully")
        return Response({
            'user': UserSerializer(user).data,
            'token': token.key,
            'message': 'Login successful'
        }, status=status.HTTP_200_OK)
    logger.warning(f"Login failed for username: {username} - Errors: {serializer.errors}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_api(request):
    """Logout user via API"""
    try:
        # Delete the user's token to log them out
        logger.info(f"User {request.user.username} logging out")
        request.user.auth_token.delete()
        logger.info(f"User {request.user.username} logged out successfully")
        return Response({
            'message': 'Logout successful'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error logging out user {request.user.username}: {str(e)}")
        return Response({
            'error': 'Error logging out'
        }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def profile_api(request):
    """Get current user profile via API"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['PUT', 'PATCH'])
@permission_classes([permissions.IsAuthenticated])
def update_profile_api(request):
    """Update current user profile via API"""
    logger.info(f"Profile update attempt for user: {request.user.username}")
    serializer = UserSerializer(request.user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        logger.info(f"Profile updated successfully for user: {request.user.username}")
        return Response({
            'user': serializer.data,
            'message': 'Profile updated successfully'
        }, status=status.HTTP_200_OK)
    logger.warning(f"Profile update failed for user: {request.user.username} - Errors: {serializer.errors}")
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def api_root(request, format=None):
    """
    API Root - Shows all available endpoints
    """
    return Response({
        'message': 'Welcome to User Management API',
        'endpoints': {
            'Authentication': {
                'register': reverse('api_register', request=request, format=format),
                'login': reverse('api_login', request=request, format=format),
                'logout': reverse('api_logout', request=request, format=format),
            },
            'Profile': {
                'profile': reverse('api_profile', request=request, format=format),
                'update_profile': reverse('api_update_profile', request=request, format=format),
            },
            'User Management': {
                'users': reverse('api_user_list', request=request, format=format),
                'user_detail': request.build_absolute_uri('/api/v1/users/{id}/'),
            },
            'Browsable API Auth': reverse('rest_framework:login', request=request, format=format),
        }
    }) 