#!/bin/bash
# Worker Connect - Start Local Development Server

echo "🚀 Starting Worker Connect Development Server..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run ./setup-local.sh first to set up the project."
    exit 1
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Check if Python is working
if ! python --version &> /dev/null; then
    echo "❌ Python not found in virtual environment"
    echo "Please run ./setup-local.sh again"
    exit 1
fi

# Run any pending migrations
echo "🗄️ Checking for database migrations..."
if ! python manage.py migrate --check &> /dev/null; then
    echo "📊 Running pending migrations..."
    python manage.py migrate
fi

echo ""
echo "🌐 Starting Django development server..."
echo ""
echo "📱 API Server: http://localhost:8000"
echo "🔧 Admin Panel: http://localhost:8000/admin/"
echo "📚 API Docs: http://localhost:8000/api/docs/"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the Django development server
python manage.py runserver 0.0.0.0:8000