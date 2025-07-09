#!/usr/bin/env python3
"""
Integration test script for Django-FastAPI authentication
"""

import os
import sys
import django
import requests
import json
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'user_management.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token

User = get_user_model()


class IntegrationTester:
    """Test Django-FastAPI integration"""
    
    def __init__(self, django_url="http://localhost:8000", fastapi_url="http://localhost:8001"):
        self.django_url = django_url
        self.fastapi_url = fastapi_url
        self.test_user_data = {
            "username": "integration_test_user",
            "email": "test@integration.com",
            "password": "TestPassword123!",
            "first_name": "Integration",
            "last_name": "Test"
        }
    
    def print_step(self, step, description):
        """Print test step"""
        print(f"\n{'='*50}")
        print(f"STEP {step}: {description}")
        print('='*50)
    
    def test_django_setup(self):
        """Test Django setup and create test user"""
        self.print_step(1, "Testing Django Setup")
        
        try:
            # Clean up existing test user
            User.objects.filter(username=self.test_user_data["username"]).delete()
            
            # Create test user
            user = User.objects.create_user(
                username=self.test_user_data["username"],
                email=self.test_user_data["email"],
                password=self.test_user_data["password"],
                first_name=self.test_user_data["first_name"],
                last_name=self.test_user_data["last_name"]
            )
            
            # Create Django token
            token, created = Token.objects.get_or_create(user=user)
            
            print(f"✅ Django user created: {user.username}")
            print(f"✅ Django token created: {token.key[:20]}...")
            
            return token.key
            
        except Exception as e:
            print(f"❌ Django setup failed: {e}")
            return None
    
    def test_django_api(self, django_token):
        """Test Django API endpoints"""
        self.print_step(2, "Testing Django API")
        
        try:
            # Test Django login
            login_response = requests.post(
                f"{self.django_url}/api/v1/auth/login/",
                json={
                    "username": self.test_user_data["username"],
                    "password": self.test_user_data["password"]
                }
            )
            
            if login_response.status_code == 200:
                print("✅ Django login successful")
                print(f"   Response: {login_response.json()}")
            else:
                print(f"❌ Django login failed: {login_response.status_code}")
                print(f"   Response: {login_response.text}")
            
            # Test Django profile endpoint
            profile_response = requests.get(
                f"{self.django_url}/api/v1/profile/",
                headers={"Authorization": f"Token {django_token}"}
            )
            
            if profile_response.status_code == 200:
                print("✅ Django profile access successful")
                return True
            else:
                print(f"❌ Django profile access failed: {profile_response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Django API test failed: {e}")
            return False
    
    def test_fastapi_health(self):
        """Test FastAPI health endpoint"""
        self.print_step(3, "Testing FastAPI Health")
        
        try:
            response = requests.get(f"{self.fastapi_url}/health")
            
            if response.status_code == 200:
                print("✅ FastAPI health check passed")
                print(f"   Response: {response.json()}")
                return True
            else:
                print(f"❌ FastAPI health check failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ FastAPI health test failed: {e}")
            return False
    
    def test_django_integration_status(self):
        """Test Django integration status in FastAPI"""
        self.print_step(4, "Testing Django Integration Status")
        
        try:
            response = requests.get(f"{self.fastapi_url}/api/auth/django-status")
            
            if response.status_code == 200:
                status_data = response.json()
                print("✅ Django integration status retrieved")
                print(f"   Integration enabled: {status_data.get('django_integration_enabled')}")
                print(f"   Available endpoints: {status_data.get('available_endpoints', [])}")
                return status_data.get('django_integration_enabled', False)
            else:
                print(f"❌ Django integration status failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Django integration status test failed: {e}")
            return False
    
    def test_cross_platform_auth(self, django_token):
        """Test cross-platform authentication"""
        self.print_step(5, "Testing Cross-Platform Authentication")
        
        try:
            # Test FastAPI with Django token
            response = requests.get(
                f"{self.fastapi_url}/api/auth/me",
                headers={"Authorization": f"Bearer {django_token}"}
            )
            
            if response.status_code == 200:
                user_data = response.json()
                print("✅ FastAPI accepts Django token")
                print(f"   User: {user_data.get('username')} ({user_data.get('email')})")
                return True
            else:
                print(f"❌ FastAPI rejected Django token: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Cross-platform auth test failed: {e}")
            return False
    
    def test_unified_token_creation(self, django_token):
        """Test unified token creation"""
        self.print_step(6, "Testing Unified Token Creation")
        
        try:
            response = requests.post(
                f"{self.fastapi_url}/api/auth/django-login",
                params={"django_token": django_token}
            )
            
            if response.status_code == 200:
                token_data = response.json()
                unified_token = token_data.get("access_token")
                print("✅ Unified token created successfully")
                print(f"   Token type: {token_data.get('token_type')}")
                print(f"   Token: {unified_token[:20]}...")
                
                # Test unified token with FastAPI
                test_response = requests.get(
                    f"{self.fastapi_url}/api/auth/me",
                    headers={"Authorization": f"Bearer {unified_token}"}
                )
                
                if test_response.status_code == 200:
                    print("✅ Unified token works with FastAPI")
                    return unified_token
                else:
                    print(f"❌ Unified token failed with FastAPI: {test_response.status_code}")
                    return None
            else:
                print(f"❌ Unified token creation failed: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Unified token test failed: {e}")
            return None
    
    def run_all_tests(self):
        """Run all integration tests"""
        print("🧪 Starting Django-FastAPI Integration Tests")
        print(f"Django URL: {self.django_url}")
        print(f"FastAPI URL: {self.fastapi_url}")
        print(f"Timestamp: {datetime.now()}")
        
        results = {
            "django_setup": False,
            "django_api": False,
            "fastapi_health": False,
            "integration_status": False,
            "cross_platform_auth": False,
            "unified_token": False
        }
        
        # Test 1: Django setup
        django_token = self.test_django_setup()
        if django_token:
            results["django_setup"] = True
            
            # Test 2: Django API
            results["django_api"] = self.test_django_api(django_token)
            
            # Test 3: FastAPI health
            results["fastapi_health"] = self.test_fastapi_health()
            
            # Test 4: Integration status
            results["integration_status"] = self.test_django_integration_status()
            
            # Test 5: Cross-platform auth
            results["cross_platform_auth"] = self.test_cross_platform_auth(django_token)
            
            # Test 6: Unified token
            unified_token = self.test_unified_token_creation(django_token)
            results["unified_token"] = unified_token is not None
        
        # Print summary
        self.print_step("FINAL", "Test Results Summary")
        total_tests = len(results)
        passed_tests = sum(results.values())
        
        for test_name, passed in results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{test_name:<20}: {status}")
        
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 All integration tests passed! Django-FastAPI integration is working perfectly.")
        else:
            print("⚠️ Some tests failed. Check the output above for details.")
        
        return results


if __name__ == "__main__":
    tester = IntegrationTester()
    results = tester.run_all_tests() 