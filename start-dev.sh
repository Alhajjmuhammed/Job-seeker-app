#!/bin/bash

# Worker Connect - Quick Start Script
# This script helps you get the project running quickly

echo "🚀 Starting Worker Connect Development Environment..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop first."
    exit 1
fi

echo "✅ Docker is running"

# Build and start services
echo "🔨 Building and starting services..."
docker-compose up -d --build

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 10

# Run migrations
echo "📊 Running database migrations..."
docker-compose exec web python manage.py migrate

# Create superuser (optional)
echo "👤 Creating superuser (optional)..."
echo "You can create a superuser now or skip this step."
read -p "Create superuser? (y/N): " create_superuser
if [[ $create_superuser =~ ^[Yy]$ ]]; then
    docker-compose exec web python manage.py createsuperuser
fi

echo ""
echo "🎉 Worker Connect is now running!"
echo ""
echo "📱 API Server: http://localhost:8000"
echo "🔧 Admin Panel: http://localhost:8000/admin/"
echo "📚 API Docs: http://localhost:8000/api/docs/"
echo ""
echo "Next steps:"
echo "1. Navigate to React-native-app/my-app/"
echo "2. Run 'npm install' to install dependencies"
echo "3. Run 'npm start' to start the mobile app"
echo ""
echo "To stop the services, run: docker-compose down"