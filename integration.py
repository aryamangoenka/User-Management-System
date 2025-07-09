"""
Django-FastAPI Integration Server
Runs both Django and FastAPI on different ports with shared authentication
"""

import asyncio
import subprocess
import signal
import sys
import time
import os
from pathlib import Path


class IntegratedServer:
    """Manages both Django and FastAPI servers"""
    
    def __init__(self):
        self.django_process = None
        self.fastapi_process = None
        self.django_port = 8000
        self.fastapi_port = 8001
        
    def start_django(self):
        """Start Django development server"""
        print(f"🚀 Starting Django server on port {self.django_port}...")
        self.django_process = subprocess.Popen([
            sys.executable, "manage.py", "runserver", f"0.0.0.0:{self.django_port}"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
    def start_fastapi(self):
        """Start FastAPI server with uvicorn"""
        print(f"⚡ Starting FastAPI server on port {self.fastapi_port}...")
        self.fastapi_process = subprocess.Popen([
            "uvicorn", "fastapi_app.main:app", 
            "--host", "0.0.0.0", 
            "--port", str(self.fastapi_port),
            "--reload"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    def stop_servers(self):
        """Stop both servers gracefully"""
        print("\n🛑 Stopping servers...")
        
        if self.django_process:
            self.django_process.terminate()
            self.django_process.wait()
            print("✅ Django server stopped")
            
        if self.fastapi_process:
            self.fastapi_process.terminate()
            self.fastapi_process.wait()
            print("✅ FastAPI server stopped")
    
    def signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        self.stop_servers()
        sys.exit(0)
    
    def check_health(self):
        """Check if both servers are healthy"""
        import requests
        try:
            # Check Django
            django_response = requests.get(f"http://localhost:{self.django_port}/", timeout=5)
            django_healthy = django_response.status_code == 200
            
            # Check FastAPI
            fastapi_response = requests.get(f"http://localhost:{self.fastapi_port}/health", timeout=5)
            fastapi_healthy = fastapi_response.status_code == 200
            
            return django_healthy, fastapi_healthy
        except Exception as e:
            return False, False
    
    def run(self):
        """Run both servers and monitor them"""
        # Set up signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            # Start both servers
            self.start_django()
            time.sleep(2)  # Give Django time to start
            self.start_fastapi()
            time.sleep(3)  # Give FastAPI time to start
            
            print("\n" + "="*60)
            print("🎉 PAKTOLUS INTEGRATED SERVER RUNNING")
            print("="*60)
            print(f"📱 Django App:  http://localhost:{self.django_port}")
            print(f"   - Admin:     http://localhost:{self.django_port}/admin")
            print(f"   - API:       http://localhost:{self.django_port}/api/v1")
            print()
            print(f"⚡ FastAPI App: http://localhost:{self.fastapi_port}")
            print(f"   - Docs:      http://localhost:{self.fastapi_port}/api/docs")
            print(f"   - Health:    http://localhost:{self.fastapi_port}/health")
            print()
            print("🔄 Integration Features:")
            print("   - Shared authentication")
            print("   - Unified user management")
            print("   - Cross-platform API access")
            print()
            print("Press Ctrl+C to stop both servers")
            print("="*60)
            
            # Monitor servers
            while True:
                time.sleep(10)
                django_healthy, fastapi_healthy = self.check_health()
                
                if not django_healthy:
                    print("⚠️  Django server appears to be down")
                if not fastapi_healthy:
                    print("⚠️  FastAPI server appears to be down")
                    
                if not (django_healthy or fastapi_healthy):
                    print("❌ Both servers are down. Exiting...")
                    break
                    
        except Exception as e:
            print(f"❌ Error running servers: {e}")
        finally:
            self.stop_servers()


if __name__ == "__main__":
    print("🔧 Paktolus Integrated Server")
    print("Starting Django + FastAPI integration...")
    
    # Ensure we're in the right directory
    if not Path("manage.py").exists():
        print("❌ Error: manage.py not found. Run this from the Django project root.")
        sys.exit(1)
    
    if not Path("fastapi_app").exists():
        print("❌ Error: fastapi_app directory not found.")
        sys.exit(1)
    
    server = IntegratedServer()
    server.run() 