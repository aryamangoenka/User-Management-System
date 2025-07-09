@echo off
REM User Management System Setup Script for Windows
REM This script automates the setup process for the User Management System

echo 🚀 Setting up User Management System...
echo ======================================

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed. Please install Python 3.8+ first.
    pause
    exit /b 1
)

REM Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js is not installed. Please install Node.js 18+ first.
    pause
    exit /b 1
)

REM Check if npm is installed
npm --version >nul 2>&1
if errorlevel 1 (
    echo ❌ npm is not installed. Please install npm first.
    pause
    exit /b 1
)

echo ✅ Prerequisites check passed!
echo.

REM Create virtual environment
echo 📦 Creating Python virtual environment...
python -m venv venv

REM Activate virtual environment
echo ⚡ Activating virtual environment...
call venv\Scripts\activate.bat

REM Install Python dependencies
echo 📚 Installing Python dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Database setup
echo 🗄️ Setting up database...
python manage.py migrate

REM Create FastAPI database tables
echo 🔧 Setting up FastAPI database...
python fastapi_app\create_tables.py

REM Frontend setup
echo 🎨 Setting up frontend...
cd frontend
npm install
cd ..

REM Create uploads directory if it doesn't exist
if not exist "uploads" mkdir uploads

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

echo.
echo ✅ Setup completed successfully!
echo.
echo 🚦 To run the application:
echo ==========================
echo.
echo 1. Django Server (Terminal 1):
echo    venv\Scripts\activate
echo    python manage.py runserver
echo.
echo 2. FastAPI Server (Terminal 2):
echo    venv\Scripts\activate
echo    cd fastapi_app
echo    uvicorn main:app --reload --port 8001
echo.
echo 3. Frontend Server (Terminal 3):
echo    cd frontend
echo    npm run dev
echo.
echo 📱 Access the application:
echo =========================
echo Frontend: http://localhost:3000
echo Django API: http://127.0.0.1:8000
echo FastAPI: http://127.0.0.1:8001
echo FastAPI Docs: http://127.0.0.1:8001/docs
echo.
echo 🎉 Happy coding!
pause 