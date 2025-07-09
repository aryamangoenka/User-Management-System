"""
Django management command to start integrated Django + FastAPI server
"""

from django.core.management.base import BaseCommand
from django.conf import settings
import subprocess
import sys
import os
import time
import signal


class Command(BaseCommand):
    help = 'Start Django and FastAPI servers in integrated mode'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--django-port',
            type=int,
            default=8000,
            help='Port for Django server (default: 8000)'
        )
        parser.add_argument(
            '--fastapi-port',
            type=int,
            default=8001,
            help='Port for FastAPI server (default: 8001)'
        )
        parser.add_argument(
            '--no-reload',
            action='store_true',
            help='Disable auto-reload for FastAPI'
        )
    
    def __init__(self):
        super().__init__()
        self.django_process = None
        self.fastapi_process = None
    
    def signal_handler(self, signum, frame):
        """Handle graceful shutdown"""
        self.stdout.write(self.style.WARNING('\nShutting down servers...'))
        if self.django_process:
            self.django_process.terminate()
        if self.fastapi_process:
            self.fastapi_process.terminate()
        sys.exit(0)
    
    def handle(self, *args, **options):
        django_port = options['django_port']
        fastapi_port = options['fastapi_port']
        reload_flag = not options['no_reload']
        
        # Set up signal handler
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        try:
            # Start Django server
            self.stdout.write(
                self.style.SUCCESS(f'Starting Django server on port {django_port}...')
            )
            
            django_cmd = [
                sys.executable, 'manage.py', 'runserver', 
                f'0.0.0.0:{django_port}', '--noreload'
            ]
            
            self.django_process = subprocess.Popen(
                django_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Give Django time to start
            time.sleep(3)
            
            # Start FastAPI server
            self.stdout.write(
                self.style.SUCCESS(f'Starting FastAPI server on port {fastapi_port}...')
            )
            
            fastapi_cmd = [
                'uvicorn', 'fastapi_app.main:app',
                '--host', '0.0.0.0',
                '--port', str(fastapi_port)
            ]
            
            if reload_flag:
                fastapi_cmd.append('--reload')
            
            self.fastapi_process = subprocess.Popen(
                fastapi_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            time.sleep(2)
            
            # Display integration info
            self.stdout.write('\n' + '='*60)
            self.stdout.write(
                self.style.SUCCESS('🎉 PAKTOLUS INTEGRATED SERVER RUNNING')
            )
            self.stdout.write('='*60)
            self.stdout.write(f'📱 Django App:  http://localhost:{django_port}')
            self.stdout.write(f'   - Admin:     http://localhost:{django_port}/admin')
            self.stdout.write(f'   - API:       http://localhost:{django_port}/api/v1')
            self.stdout.write('')
            self.stdout.write(f'⚡ FastAPI App: http://localhost:{fastapi_port}')
            self.stdout.write(f'   - Docs:      http://localhost:{fastapi_port}/api/docs')
            self.stdout.write(f'   - Health:    http://localhost:{fastapi_port}/health')
            self.stdout.write('')
            self.stdout.write('🔄 Integration Features:')
            self.stdout.write('   - Shared authentication')
            self.stdout.write('   - Unified user management')
            self.stdout.write('   - Cross-platform API access')
            self.stdout.write('')
            self.stdout.write('Press Ctrl+C to stop both servers')
            self.stdout.write('='*60)
            
            # Monitor processes
            while True:
                time.sleep(1)
                
                if self.django_process.poll() is not None:
                    self.stdout.write(
                        self.style.ERROR('Django server stopped unexpectedly')
                    )
                    break
                    
                if self.fastapi_process.poll() is not None:
                    self.stdout.write(
                        self.style.ERROR('FastAPI server stopped unexpectedly')
                    )
                    break
                    
        except KeyboardInterrupt:
            self.signal_handler(None, None)
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error starting servers: {e}')
            )
        finally:
            # Clean up
            if self.django_process:
                self.django_process.terminate()
            if self.fastapi_process:
                self.fastapi_process.terminate() 