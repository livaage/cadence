# Development Guide

This guide will help you understand the codebase structure and how to contribute to the Code Competition Platform.

## Architecture Overview

The platform consists of several interconnected services:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │   Database      │
│   (React)       │◄──►│   (FastAPI)     │◄──►│  (PostgreSQL)   │
│   Port: 3000    │    │   Port: 8000    │    │   Port: 5432    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │  Code Executor  │
                       │   (Docker)      │
                       └─────────────────┘
```

## Technology Stack

### Frontend
- **React 18** with TypeScript
- **Material-UI (MUI)** for UI components
- **React Router** for navigation
- **Axios** for API communication
- **Recharts** for data visualization

### Backend
- **FastAPI** (Python web framework)
- **SQLAlchemy** (ORM)
- **PostgreSQL** (Database)
- **Redis** (Caching/Queue)
- **Docker** (Code execution sandbox)

### Infrastructure
- **Docker Compose** for orchestration
- **PostgreSQL** for data persistence
- **Redis** for caching and job queues

## Project Structure

```
competition_page/
├── frontend/                 # React application
│   ├── public/              # Static files
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── contexts/        # React contexts
│   │   ├── services/        # API services
│   │   └── index.tsx        # Entry point
│   ├── package.json
│   └── Dockerfile
├── backend/                  # FastAPI application
│   ├── models.py            # Database models
│   ├── schemas.py           # Pydantic schemas
│   ├── database.py          # Database connection
│   ├── auth.py              # Authentication
│   ├── code_executor.py     # Code execution logic
│   ├── main.py              # FastAPI app
│   ├── requirements.txt
│   └── Dockerfile
├── docker/
│   └── code-executor/       # Code execution service
├── database/
│   └── init.sql             # Database initialization
├── docker-compose.yml       # Service orchestration
├── setup.sh                 # Setup script
└── README.md
```

## Development Setup

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ and npm
- Python 3.9+

### Quick Start
1. Clone the repository
2. Run the setup script:
   ```bash
   ./setup.sh
   ```

### Manual Setup
1. **Start the infrastructure:**
   ```bash
   docker-compose up -d postgres redis
   ```

2. **Set up the backend:**
   ```bash
   cd backend
   pip install -r requirements.txt
   python main.py
   ```

3. **Set up the frontend:**
   ```bash
   cd frontend
   npm install
   npm start
   ```

## API Documentation

### Public Endpoints
- `GET /problems` - Get all active problems
- `GET /problems/{id}` - Get specific problem
- `POST /submissions` - Submit code solution
- `GET /submissions/{id}` - Get submission status

### Teacher Endpoints (Protected)
- `POST /auth/login` - Teacher login
- `GET /teacher/problems` - Get all problems
- `POST /teacher/problems` - Create new problem
- `GET /teacher/submissions` - Get all submissions
- `GET /teacher/submissions/{id}` - Get detailed submission
- `GET /teacher/stats` - Get problem statistics

## Database Schema

### Core Tables
- **problems** - Programming problems
- **test_cases** - Test cases for problems
- **submissions** - Student code submissions
- **test_results** - Results of test case execution
- **teachers** - Teacher accounts

### Relationships
- Problems have many test cases
- Problems have many submissions
- Submissions have many test results
- Test results belong to submissions and test cases

## Code Execution

### Security Features
- Docker container isolation
- Resource limits (CPU, memory, time)
- Network disabled
- Privilege dropping
- Read-only file systems where possible

### Supported Languages
- **Python 3.11** - Using python:3.11-slim image
- **C++17** - Using gcc:11 image with optimization

### Execution Flow
1. Student submits code
2. Backend creates submission record
3. Background task evaluates against test cases
4. Each test case runs in isolated Docker container
5. Results are stored and aggregated
6. Student can view final results

## Adding New Features

### Adding a New Problem
1. Create problem via teacher dashboard or API
2. Add test cases with input/output pairs
3. Set difficulty, time limits, and memory limits

### Adding a New Language
1. Update `code_executor.py` with new language handler
2. Add Docker image configuration
3. Update frontend language selector
4. Add language validation in backend

### Adding New Test Case Types
1. Extend the test case model
2. Update evaluation logic
3. Modify frontend to display new test types

## Testing

### Backend Testing
```bash
cd backend
python -m pytest tests/
```

### Frontend Testing
```bash
cd frontend
npm test
```

### Integration Testing
```bash
# Start the full stack
docker-compose up -d

# Run integration tests
python -m pytest tests/integration/
```

## Deployment

### Production Considerations
1. **Security:**
   - Change default passwords
   - Use strong secret keys
   - Enable HTTPS
   - Configure proper CORS

2. **Performance:**
   - Use production database
   - Configure Redis for caching
   - Set up load balancing
   - Monitor resource usage

3. **Monitoring:**
   - Add logging
   - Set up health checks
   - Monitor Docker containers
   - Track API performance

### Docker Production
```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Common Issues

1. **Docker containers not starting:**
   ```bash
   docker-compose logs
   docker system prune -a
   ```

2. **Database connection issues:**
   ```bash
   docker-compose restart postgres
   docker-compose exec postgres psql -U competition_user -d competition_db
   ```

3. **Code execution failures:**
   ```bash
   docker-compose logs code-executor
   docker system prune -f
   ```

4. **Frontend build issues:**
   ```bash
   cd frontend
   rm -rf node_modules package-lock.json
   npm install
   ```

### Performance Tuning
- Adjust Docker resource limits
- Optimize database queries
- Configure Redis caching
- Monitor memory usage

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Code Style
- **Python:** Follow PEP 8
- **JavaScript/TypeScript:** Use ESLint and Prettier
- **SQL:** Use consistent formatting
- **Docker:** Follow best practices

## License

This project is licensed under the MIT License - see the LICENSE file for details. 