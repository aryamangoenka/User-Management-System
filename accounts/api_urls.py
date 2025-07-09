from django.urls import path
from . import api_views

urlpatterns = [
    # API Root
    path('', api_views.api_root, name='api_root'),
    
    # Authentication endpoints
    path('auth/register/', api_views.register_api, name='api_register'),
    path('auth/login/', api_views.login_api, name='api_login'),
    path('auth/logout/', api_views.logout_api, name='api_logout'),
    
    # User profile endpoints
    path('profile/', api_views.profile_api, name='api_profile'),
    path('profile/update/', api_views.update_profile_api, name='api_update_profile'),
    
    # User management endpoints
    path('users/', api_views.UserListCreateAPIView.as_view(), name='api_user_list'),
    path('users/<int:pk>/', api_views.UserDetailAPIView.as_view(), name='api_user_detail'),
] 