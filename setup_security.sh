#!/bin/bash

# Worker Connect - Quick Security Setup Script
# This script helps set up security configurations

set -e  # Exit on error

echo "🔒 Worker Connect - Security Setup"
echo "=================================="
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv .venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔌 Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip -q

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt -q
echo "✅ Dependencies installed"

# Check if .env exists
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  .env file not found!"
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    
    # Generate SECRET_KEY
    echo ""
    echo "🔑 Generating SECRET_KEY..."
    SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
    
    # Update .env with generated SECRET_KEY
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|SECRET_KEY=your-secret-key-here-CHANGE-THIS-IN-PRODUCTION|SECRET_KEY=$SECRET_KEY|g" .env
    else
        # Linux
        sed -i "s|SECRET_KEY=your-secret-key-here-CHANGE-THIS-IN-PRODUCTION|SECRET_KEY=$SECRET_KEY|g" .env
    fi
    
    echo "✅ SECRET_KEY generated and saved to .env"
    echo ""
    echo "⚠️  IMPORTANT: Review your .env file and update settings for your environment"
else
    echo "✅ .env file already exists"
fi

# Create logs directory if it doesn't exist
if [ ! -d "logs" ]; then
    echo "📁 Creating logs directory..."
    mkdir -p logs
    echo "✅ Logs directory created"
fi

# Run migrations
echo ""
echo "🔄 Running database migrations..."
python manage.py makemigrations
python manage.py migrate
echo "✅ Migrations complete"

# Run security check
echo ""
echo "🔒 Running security audit..."
python manage.py check_security
echo ""

# Run Django deployment check
echo "🔍 Running Django deployment check..."
python manage.py check --deploy
echo ""

echo "=================================="
echo "✅ Security setup complete!"
echo "=================================="
echo ""
echo "📋 Next steps:"
echo "  1. Review your .env file and update any necessary settings"
echo "  2. For production, set DEBUG=False in .env"
echo "  3. Add your production domain to ALLOWED_HOSTS in .env"
echo "  4. Review SECURITY.md for complete security checklist"
echo "  5. Run: python manage.py createsuperuser (if needed)"
echo "  6. Run: python manage.py runserver (to start development server)"
echo ""
echo "📚 Documentation:"
echo "  - SECURITY.md - Complete security guide"
echo "  - README.md - Project setup instructions"
echo ""
