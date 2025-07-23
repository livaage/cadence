#!/bin/bash

# Code Competition Platform Setup Script
# This script will help you set up the complete system

set -e

echo "🚀 Setting up Code Competition Platform..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed (try both old and new syntax)
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p submissions tests

# Set up environment variables
echo "🔧 Setting up environment variables..."
if [ ! -f .env ]; then
    cat > .env << EOF
# Database Configuration
DATABASE_URL=postgresql://competition_user:competition_password@postgres:5432/competition_db
POSTGRES_DB=competition_db
POSTGRES_USER=competition_user
POSTGRES_PASSWORD=competition_password

# Security
SECRET_KEY=your-secret-key-change-in-production

# Redis Configuration
REDIS_URL=redis://redis:6379

# Code Execution Limits
MAX_EXECUTION_TIME=30
MAX_MEMORY=512m
MAX_CPU=1.0

# Frontend Configuration
REACT_APP_API_URL=http://localhost:8000

# GitHub Integration (Optional)
# Get your GitHub token from: https://github.com/settings/tokens
# Required scopes: repo, read:user, read:email
GITHUB_TOKEN=your-github-token-here
EOF
    echo "✅ Created .env file"
else
    echo "✅ .env file already exists"
fi

# Build and start services
echo "🐳 Building and starting Docker services..."
docker compose build

echo "🚀 Starting services..."
docker compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 30

# Check if services are running
echo "🔍 Checking service status..."
if docker compose ps | grep -q "Up"; then
    echo "✅ All services are running!"
else
    echo "❌ Some services failed to start. Check logs with: docker compose logs"
    exit 1
fi

# Display access information
echo ""
echo "🎉 Setup complete! Your Code Competition Platform is ready."
echo ""
echo "📱 Access URLs:"
echo "   Student Interface: http://localhost:3000"
echo "   Teacher Dashboard: http://localhost:3000/teacher"
echo "   API Documentation: http://localhost:8000/docs"
echo ""
echo "🔐 Teacher Login:"
echo "   Username: admin"
echo "   Password: teacher123"
echo ""
echo "📋 Useful Commands:"
echo "   View logs: docker compose logs -f"
echo "   Stop services: docker compose down"
echo "   Restart services: docker compose restart"
echo "   Update code: docker compose up -d --build"
echo ""
echo "📚 Sample Problems Available:"
echo "   - Hello World (Easy)"
echo "   - Sum of Two Numbers (Easy)"
echo "   - Fibonacci Sequence (Medium)"
echo "   - Sort Array (Medium)"
echo "   - Prime Number Check (Hard)"
echo ""
echo "🔧 For development:"
echo "   Frontend: cd frontend && npm install && npm start"
echo "   Backend: cd backend && pip install -r requirements.txt && python main.py"
echo ""
echo "Happy coding! 🎯" 