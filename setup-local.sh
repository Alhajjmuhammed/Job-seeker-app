#!/bin/bash
# Worker Connect - Local Development Setup Script for Linux/Mac

echo "🚀 Setting up Worker Connect for Local Development..."

# Check if Python is available
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
    echo "✅ Python3 is available"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
    echo "✅ Python is available"
else
    echo "❌ Python is not available"
    echo ""
    echo "Please install Python 3.11+ from https://python.org"
    echo "Or on Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-pip python3-venv"
    echo "Or on macOS with Homebrew: brew install python"
    echo ""
    echo "After installing Python, run this script again."
    exit 1
fi

# Create virtual environment
echo "📦 Creating virtual environment..."
$PYTHON_CMD -m venv venv

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📚 Installing Python dependencies..."
pip install -r requirements-local.txt

# Optional: Install full requirements if needed
echo ""
read -p "Install full requirements including optional packages? (y/N): " full_install
if [[ $full_install =~ ^[Yy]$ ]]; then
    echo "📦 Installing full requirements..."
    pip install -r requirements.txt
fi

# Create .env if it doesn't exist (it should exist now)
if [ ! -f .env ]; then
    echo "📝 Copying environment configuration..."
    cp .env.example .env
fi

# Run migrations
echo "🗄️ Setting up database..."
python manage.py migrate

# Create superuser (optional)
echo "👤 Create superuser account? (optional)"
read -p "Create superuser? (y/N): " create_superuser
if [[ $create_superuser =~ ^[Yy]$ ]]; then
    python manage.py createsuperuser
fi

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

echo ""
echo "🎉 Setup complete!"
echo ""
echo "To start the development server:"
echo "  1. Run: ./start-local.sh"
echo "  2. Or manually: source venv/bin/activate && python manage.py runserver"
echo ""
echo "The API will be available at: http://localhost:8000"