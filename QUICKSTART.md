# Quick Start Guide

Get your Code Competition Platform up and running in minutes!

## 🚀 One-Command Setup

```bash
# Clone and setup (if you have the repository)
./setup.sh

# Or if you're starting from scratch:
git clone <repository-url>
cd competition_page
./setup.sh
```

## 📋 Prerequisites

- **Docker** and **Docker Compose** installed
- At least 4GB of available RAM
- 10GB of free disk space

### Installing Docker

**macOS:**
```bash
# Using Homebrew
brew install --cask docker

# Or download from https://docs.docker.com/desktop/mac/install/
```

**Linux (Ubuntu/Debian):**
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

**Windows:**
Download Docker Desktop from https://docs.docker.com/desktop/windows/install/

## 🎯 What You'll Get

After running the setup, you'll have:

- **Student Interface** at http://localhost:3000
- **Teacher Dashboard** at http://localhost:3000/teacher  
- **API Documentation** at http://localhost:8000/docs

> **Note for Production**: Students access the platform via a public URL (e.g., `https://competition.yourschool.edu`). The localhost URLs are only for development and testing.

## 🔐 Default Login

**Teacher Account:**
- Username: `admin`
- Password: `teacher123`

## 📚 Sample Problems

The system comes with 5 pre-configured problems:

1. **Hello World** (Easy) - Print "Hello, World!"
2. **Sum of Two Numbers** (Easy) - Add two integers
3. **Fibonacci Sequence** (Medium) - Generate Fibonacci numbers
4. **Sort Array** (Medium) - Sort an array of integers
5. **Prime Number Check** (Hard) - Check if a number is prime

## 🧪 Testing the System

### As a Student:
1. Go to http://localhost:3000
2. Click on any problem
3. Enter your name and code
4. Submit and see results!

### As a Teacher:
1. Go to http://localhost:3000/teacher
2. Login with admin/teacher123
3. View submissions and analytics
4. Create new problems

## 🛠️ Common Commands

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down

# Restart services
docker-compose restart

# Update after code changes
docker-compose up -d --build
```

## 🔧 Troubleshooting

### Services won't start?
```bash
# Check Docker is running
docker --version
docker-compose --version

# Check available resources
docker system df

# Clean up and retry
docker system prune -a
./setup.sh
```

### Can't access the website?
```bash
# Check if services are running
docker-compose ps

# Check logs
docker-compose logs frontend
docker-compose logs backend
```

### Database issues?
```bash
# Restart database
docker-compose restart postgres

# Check database logs
docker-compose logs postgres
```

## 📊 What's Included

### Frontend Features:
- ✅ Modern React interface
- ✅ Code editor with syntax highlighting
- ✅ Real-time submission status
- ✅ Responsive design

### Backend Features:
- ✅ FastAPI with automatic documentation
- ✅ PostgreSQL database
- ✅ JWT authentication
- ✅ Background task processing

### Code Execution:
- ✅ Docker-based sandboxing
- ✅ Python 3.11 support
- ✅ C++17 support
- ✅ Resource limits and timeouts
- ✅ Security isolation

### Teacher Features:
- ✅ Analytics dashboard
- ✅ Submission management
- ✅ Problem creation
- ✅ Performance metrics

## 🎉 Next Steps

1. **Customize Problems:** Add your own programming challenges
2. **Configure Limits:** Adjust time and memory limits
3. **Add Languages:** Extend support for more programming languages
4. **Deploy:** Set up for production use

## 📞 Need Help?

- Check the logs: `docker-compose logs`
- Review the full documentation in `DEVELOPMENT.md`
- Check the API docs at http://localhost:8000/docs

Happy coding! 🎯 