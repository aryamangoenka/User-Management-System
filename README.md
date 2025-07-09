# User Management System

A comprehensive user management application built with Django, FastAPI, and Next.js featuring user authentication, profile management, and role-based access control.

## 🏗️ Architecture

- **Backend**: Django with Django REST Framework + FastAPI integration
- **Frontend**: Next.js 15 with TypeScript and Tailwind CSS
- **Database**: SQLite (development) - easily configurable for PostgreSQL/MySQL
- **Authentication**: JWT-based authentication with session management
- **File Upload**: Profile picture upload functionality

## 🚀 Features

- User registration and authentication
- Profile picture upload and management
- Role-based access control (Admin, Manager, User)
- Mandatory phone number and address fields
- Account lockout protection with django-axes
- Modern responsive UI with shadcn/ui components
- RESTful API with FastAPI integration
- Comprehensive logging and error handling

## 📋 Prerequisites

Before running the application, ensure you have the following installed:

- **Python 3.8+** (tested with Python 3.9+)
- **Node.js 18+** (for Next.js frontend)
- **npm or yarn** (package manager)
- **Git** (for version control)

## 🛠️ Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/aryamangoenka/User-Management-System.git
cd User-Management-System
```

### 2. Backend Setup (Django + FastAPI)

#### Create and Activate Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

#### Install Python Dependencies

```bash
pip install -r requirements.txt
```

#### Database Setup

```bash
# Run database migrations
python manage.py migrate

# Create superuser (admin account)
python manage.py createsuperuser
```

#### Create FastAPI Database Tables

```bash
# Initialize FastAPI database
python fastapi_app/create_tables.py
```

### 3. Frontend Setup (Next.js)

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Return to project root
cd ..
```

## 🚦 Running the Application

### Start the Backend Services

You need to run both Django and FastAPI servers:

#### Terminal 1 - Django Server

```bash
# Make sure virtual environment is activated
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows

# Start Django development server
python manage.py runserver
```

Django will run on: `http://127.0.0.1:8000/`

#### Terminal 2 - FastAPI Server

```bash
# Make sure virtual environment is activated
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows

# Start FastAPI server
cd fastapi_app
uvicorn main:app --reload --port 8001
```

FastAPI will run on: `http://127.0.0.1:8001/`

### Start the Frontend

#### Terminal 3 - Next.js Frontend

```bash
cd frontend
npm run dev
```

Next.js will run on: `http://localhost:3000/` (or `http://localhost:3001/` if 3000 is in use)

## 📚 Key Dependencies

### Backend Dependencies

```
Django==5.2.1
djangorestframework==3.15.2
django-cors-headers==4.3.1
django-axes==6.1.1
PyJWT==2.8.0
Pillow==10.4.0
fastapi==0.111.0
uvicorn[standard]==0.30.1
python-multipart==0.0.9
pydantic==2.7.4
sqlalchemy==2.0.31
pytest==8.2.2
pytest-django==4.8.0
requests==2.32.3
```

### Frontend Dependencies

```
next: ^15.3.3
react: ^18.3.1
typescript: ^5.6.3
tailwindcss: ^3.4.1
@radix-ui/react-*: (various UI components)
lucide-react: ^0.460.0
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database Configuration (optional)
DATABASE_URL=sqlite:///db.sqlite3

# FastAPI Settings
FASTAPI_SECRET_KEY=your-fastapi-secret-key
```

### API Endpoints

#### Django REST API

- Base URL: `http://127.0.0.1:8000/api/v1/`
- Authentication: `/api/v1/auth/login/`
- Registration: `/api/v1/auth/register/`
- Profile: `/api/v1/auth/profile/`
- Users: `/api/v1/users/`

#### FastAPI

- Base URL: `http://127.0.0.1:8001/`
- Interactive Docs: `http://127.0.0.1:8001/docs`
- Users: `/users/`
- Authentication: `/auth/`
- File Upload: `/files/`

## 🧪 Testing

### Run Backend Tests

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Run Django tests
python manage.py test

# Run FastAPI tests
pytest fastapi_app/tests/

# Run integration tests
pytest test_integration.py -v
```

### Frontend Testing

```bash
cd frontend
npm run test  # If test scripts are configured
```

## 🗄️ Database Models

### Django CustomUser Model

- `username`: Unique username
- `email`: Email address
- `first_name`: First name
- `last_name`: Last name
- `phone_number`: Phone number (mandatory)
- `address`: Address (mandatory)
- `profile_picture`: Profile image upload
- `role`: User role (USER, MANAGER, ADMIN)
- `date_joined`: Registration date
- `last_login`: Last login timestamp

### FastAPI Models

- User management with SQLAlchemy
- Product management
- File upload handling

## 📁 Project Structure

```
User-Management-System/
├── accounts/                 # Django user app
│   ├── models.py            # CustomUser model
│   ├── serializers.py       # API serializers
│   ├── api_views.py         # API endpoints
│   └── views.py             # Web views
├── fastapi_app/             # FastAPI application
│   ├── main.py              # FastAPI main app
│   ├── models.py            # SQLAlchemy models
│   ├── routers/             # API routers
│   └── tests/               # FastAPI tests
├── frontend/                # Next.js frontend
│   ├── src/
│   │   ├── app/             # App router pages
│   │   ├── components/      # React components
│   │   └── lib/             # Utilities and API config
│   └── package.json
├── user_management/         # Django project settings
├── templates/               # Django templates
├── uploads/                 # File upload directory
├── requirements.txt         # Python dependencies
└── manage.py               # Django management script
```

## 🔐 Default User Roles

- **ADMIN**: Full system access, user management
- **MANAGER**: Limited administrative access
- **USER**: Basic user access, profile management

## 🚨 Troubleshooting

### Common Issues

1. **Port conflicts**: If ports 3000, 8000, or 8001 are in use, the applications will automatically use alternative ports.

2. **Virtual environment issues**: Make sure the virtual environment is activated before running Python commands.

3. **Database migrations**: If you encounter database errors, try:

   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

4. **Frontend dependencies**: If npm install fails, try:

   ```bash
   rm -rf node_modules package-lock.json
   npm install
   ```

5. **CORS issues**: The Django settings include CORS configuration for localhost. Adjust `CORS_ALLOWED_ORIGINS` in settings.py if needed.

### Log Files

- Application logs are stored in the `logs/` directory
- Check Django server output for backend issues
- Check browser console for frontend issues

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📞 Support

For support or questions, please open an issue on the GitHub repository.

---

**Happy coding! 🎉**
