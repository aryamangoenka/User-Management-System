from django.contrib.auth.models import AbstractUser
from django.db import models

# Create your models here.

class CustomUser(AbstractUser):
    # Note: user_id is the default 'id' field (primary key)
    # Note: username, email, password, first_name, last_name, is_active, last_login 
    # are inherited from AbstractUser
    
    phone_number = models.CharField(max_length=15, blank=False, verbose_name="Phone")
    address = models.TextField(blank=False)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    
    # Role field with choices
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('manager', 'Manager'),
        ('user', 'User'),
        ('staff', 'Staff'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.username

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ['-created_at']
