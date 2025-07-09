# 🚀 Quick Start Guide

Get the User Management System running in under 5 minutes!

## Option 1: Automated Setup (Recommended)

### For macOS/Linux:

```bash
./setup.sh
```

### For Windows:

```cmd
setup.bat
```

## Option 2: Manual Setup

### 1. Backend Setup

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Setup database
python manage.py migrate
python fastapi_app/create_tables.py
```

### 2. Frontend Setup

```bash
cd frontend
npm install
cd ..
```

## 🏃‍♂️ Running the App

Open **3 separate terminals** and run:

### Terminal 1 - Django (Port 8000)

```bash
source venv/bin/activate
python manage.py runserver
```

### Terminal 2 - FastAPI (Port 8001)

```bash
source venv/bin/activate
cd fastapi_app
uvicorn main:app --reload --port 8001
```

### Terminal 3 - Frontend (Port 3000)

```bash
cd frontend
npm run dev
```

## 🌐 Access Points

- **Frontend**: http://localhost:3000
- **Django API**: http://127.0.0.1:8000
- **FastAPI**: http://127.0.0.1:8001
- **API Docs**: http://127.0.0.1:8001/docs

## 👤 First Steps

1. Visit http://localhost:3000
2. Click "Register" to create an account
3. Fill in all required fields (phone and address are mandatory)
4. Upload a profile picture
5. Login and explore!

## ⚡ Need Help?

- Check the full [README.md](README.md) for detailed instructions
- Look at the troubleshooting section if you encounter issues
- All logs are in the `logs/` directory

---

**That's it! You're ready to go! 🎉**
