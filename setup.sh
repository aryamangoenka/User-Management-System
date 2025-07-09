#!/bin/bash

# User Management System Setup Script
# This script automates the setup process for the User Management System

set -e  # Exit on any error

echo "🚀 Setting up User Management System..."
echo "======================================"

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm first."
    exit 1
fi

echo "✅ Prerequisites check passed!"
echo ""

# Create virtual environment
echo "📦 Creating Python virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "⚡ Activating virtual environment..."
source venv/bin/activate

# Install Python dependencies
echo "📚 Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Database setup
echo "🗄️  Setting up database..."
python manage.py migrate

# Create FastAPI database tables
echo "🔧 Setting up FastAPI database..."
python fastapi_app/create_tables.py

# Frontend setup
echo "🎨 Setting up frontend..."
cd frontend
npm install
cd ..

# Create uploads directory if it doesn't exist
mkdir -p uploads

# Create logs directory if it doesn't exist
mkdir -p logs

echo ""
echo "✅ Setup completed successfully!"
echo ""
echo "🚦 To run the application:"
echo "=========================="
echo ""
echo "1. Django Server (Terminal 1):"
echo "   source venv/bin/activate"
echo "   python manage.py runserver"
echo ""
echo "2. FastAPI Server (Terminal 2):"
echo "   source venv/bin/activate"
echo "   cd fastapi_app"
echo "   uvicorn main:app --reload --port 8001"
echo ""
echo "3. Frontend Server (Terminal 3):"
echo "   cd frontend"
echo "   npm run dev"
echo ""
echo "📱 Access the application:"
echo "========================="
echo "Frontend: http://localhost:3000"
echo "Django API: http://127.0.0.1:8000"
echo "FastAPI: http://127.0.0.1:8001"
echo "FastAPI Docs: http://127.0.0.1:8001/docs"
echo ""
echo "🎉 Happy coding!" 