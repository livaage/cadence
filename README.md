# Code Competition Platform

A comprehensive web-based platform for programming competitions and coding assessments. Students can submit code solutions in C++ or Python, which are automatically evaluated for accuracy and performance. Teachers get detailed analytics and can manage problems, view submissions, and track student progress.

## 🚀 Features

### For Students
- **Web-based Code Editor**: Write and submit code directly in the browser
- **Multiple Languages**: Support for Python and C++ with syntax highlighting
- **Real-time Results**: Get immediate feedback on code execution and test results
- **Performance Metrics**: See execution time and memory usage for your solutions
- **No Installation Required**: Everything works through a web browser

### For Teachers
- **Problem Management**: Create and manage programming problems with test cases
- **Submission Analytics**: View detailed statistics on student performance
- **Individual Review**: Inspect each student's solution and test results
- **Performance Tracking**: Monitor average scores, execution times, and success rates
- **GitHub Integration**: Create repositories for students to push their work and automatically sync and evaluate commits

### Technical Features
- **Secure Code Execution**: Docker-based sandboxing with resource limits
- **Real-time Processing**: Background task processing for code evaluation
- **Scalable Architecture**: Microservices design with PostgreSQL, Redis, and FastAPI
- **Modern UI**: React frontend with Material-UI components
- **API-First Design**: RESTful API with comprehensive documentation

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Backend      │    │  Code Executor  │
│   (React)       │◄──►│   (FastAPI)     │◄──►│   (Docker)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   PostgreSQL    │
                       │   (Database)    │
                       └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │     Redis       │
                       │   (Cache/Queue) │
                       └─────────────────┘
```

## 🛠️ Technology Stack

- **Frontend**: React 18, TypeScript, Material-UI, Recharts
- **Backend**: FastAPI, SQLAlchemy, Pydantic, Celery
- **Database**: PostgreSQL 15
- **Cache/Queue**: Redis 7
- **Code Execution**: Docker containers with resource limits
- **Authentication**: JWT tokens with bcrypt password hashing
- **GitHub Integration**: PyGithub, GitPython

## 📦 Installation

### For Development (Local Setup)

**Prerequisites:**
- Docker and Docker Compose
- Git

**Quick Start:**

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd competition_page
   ```

2. **Run the setup script**:
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```

3. **Access the platform**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### For Production (Student Access)

**Students do NOT need to run anything locally!** They access the platform through a public URL.

**For Teachers/Administrators:**

1. **Deploy to a cloud server** (AWS, Google Cloud, DigitalOcean, etc.)
2. **Configure a domain name** (e.g., `competition.yourschool.edu`)
3. **Students access via**: `https://competition.yourschool.edu`

**Example deployment scenarios:**

- **School/University**: Deploy on institutional servers with domain like `coding.yourschool.edu`
- **Online Course**: Deploy on cloud platform with domain like `coding-course.com`
- **Competition**: Deploy on cloud platform with domain like `hackathon-2024.com`

**Students simply:**
1. Visit the public URL
2. Start coding immediately
3. No installation required

### Default Credentials
- **Teacher Login**: admin / teacher123
- **Database**: competition_user / competition_password

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# Database Configuration
POSTGRES_DB=competition_db
POSTGRES_USER=competition_user
POSTGRES_PASSWORD=competition_password

# Backend Configuration
SECRET_KEY=your-secret-key-change-in-production
DATABASE_URL=postgresql://competition_user:competition_password@postgres:5432/competition_db
REDIS_URL=redis://redis:6379

# GitHub Integration (Optional)
GITHUB_TOKEN=your-github-token-here

# Frontend Configuration
REACT_APP_API_URL=http://localhost:8000
```

### GitHub Integration Setup

To enable GitHub integration for repository management:

1. **Create a GitHub Personal Access Token**:
   - Go to GitHub Settings → Developer settings → Personal access tokens
   - Generate a new token with scopes: `repo`, `read:user`, `read:email`
   - Copy the token

2. **Add the token to your `.env` file**:
   ```env
   GITHUB_TOKEN=ghp_your_token_here
   ```

3. **Restart the services**:
   ```bash
   docker-compose restart backend
   ```

## 📚 Usage

### For Teachers

#### 1. Initial Setup
1. **Login**: Use the default credentials (admin/teacher123)
2. **Create Problems**: Add programming problems with test cases
3. **View Analytics**: Monitor student performance and statistics

#### 2. GitHub Integration Workflow

**Setting up GitHub Integration:**

1. **Create a GitHub Personal Access Token**:
   - Go to GitHub Settings → Developer settings → Personal access tokens
   - Click "Generate new token (classic)"
   - Select scopes: `repo`, `read:user`, `read:email`
   - Copy the generated token

2. **Configure the Platform**:
   - Add your GitHub token to the `.env` file: `GITHUB_TOKEN=ghp_your_token_here`
   - Restart the backend: `docker-compose restart backend`

3. **Create GitHub Repositories for Problems**:
   - Go to the Teacher Dashboard
   - Click "GitHub Integration" in the navigation
   - Click "Create Repository" for a specific problem
   - The system will create a private GitHub repository for that problem

**Managing Student Submissions via GitHub:**

1. **Repository Structure**: Each repository will have:
   ```
   problem-name/
   ├── README.md (problem description)
   ├── test-cases/ (hidden test cases)
   └── student-submissions/ (where students add their work)
   ```

2. **Student Instructions**: Share these instructions with students:
   - Clone the repository: `git clone <repository-url>`
   - Create a folder with your name: `mkdir your-name`
   - Add your solution files to your folder
   - Commit and push: `git add . && git commit -m "Your solution" && git push`

3. **Automatic Evaluation**:
   - Click "Sync Repository" in the GitHub Integration dashboard
   - The system will automatically:
     - Fetch all student commits
     - Evaluate each student's code against test cases
     - Update the dashboard with results

#### 3. Review and Analytics

1. **View All Submissions**: See all student submissions with detailed results
2. **Individual Review**: Click on any submission to see:
   - Student's code
   - Test case results
   - Execution time and memory usage
   - Error messages (if any)

3. **Analytics Dashboard**: Monitor:
   - Problem success rates
   - Average scores
   - Common error patterns
   - Performance metrics

### For Students

#### 1. Web-based Submission
1. **Browse Problems**: View available programming challenges
2. **Write Code**: Use the built-in code editor with syntax highlighting
3. **Submit Solutions**: Get immediate feedback and results
4. **View Results**: See detailed test case results and performance metrics

#### 2. GitHub-based Submission (if enabled by teacher)
1. **Get Repository Access**: Teacher will provide a GitHub repository URL
2. **Clone the Repository**: `git clone <repository-url>`
3. **Create Your Workspace**: 
   ```bash
   cd problem-name
   mkdir your-name
   cd your-name
   ```
4. **Add Your Solution**: Create your solution files (e.g., `solution.py`, `solution.cpp`)
5. **Commit and Push**:
   ```bash
   git add .
   git commit -m "My solution for [Problem Name]"
   git push origin main
   ```
6. **Wait for Evaluation**: The teacher will sync the repository to evaluate your code

#### 3. Supported Languages and Formats

**Python Solutions**:
```python
# solution.py
def main():
    # Read input
    n = int(input())
    
    # Your solution here
    result = n * 2
    
    # Print output
    print(result)

if __name__ == "__main__":
    main()
```

**C++ Solutions**:
```cpp
// solution.cpp
#include <iostream>
using namespace std;

int main() {
    // Read input
    int n;
    cin >> n;
    
    // Your solution here
    int result = n * 2;
    
    // Print output
    cout << result << endl;
    
    return 0;
}
```

## 🔒 Security Features

- **Docker Sandboxing**: Code execution in isolated containers
- **Resource Limits**: CPU, memory, and execution time restrictions
- **Network Isolation**: Disabled network access for code execution
- **Privilege Dropping**: Non-root execution in containers
- **Input Validation**: Comprehensive input sanitization
- **JWT Authentication**: Secure teacher authentication

## 📊 API Documentation

The API is fully documented with OpenAPI/Swagger:
- **Interactive Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Key Endpoints

#### Public Endpoints
- `GET /problems` - List all active problems
- `GET /problems/{id}` - Get problem details
- `POST /submissions` - Submit code for evaluation
- `GET /submissions/{id}` - Get submission status

#### Teacher Endpoints (Protected)
- `POST /auth/login` - Teacher authentication
- `GET /teacher/problems` - Manage problems
- `POST /teacher/problems` - Create new problems
- `GET /teacher/submissions` - View all submissions
- `GET /teacher/stats` - Get analytics data

#### GitHub Integration Endpoints
- `POST /teacher/github/repos` - Create GitHub repository
- `GET /teacher/github/repos` - List repositories
- `POST /teacher/github/sync` - Sync repository commits
- `GET /teacher/github/repos/{id}/commits` - View student commits

## 🚀 Deployment

### Production Deployment

**For Students to Access the Platform:**

1. **Deploy to a Cloud Server**:
   - **AWS**: Use EC2 with Docker or ECS
   - **Google Cloud**: Use Compute Engine or Cloud Run
   - **DigitalOcean**: Use Droplets with Docker
   - **Heroku**: Use container deployment
   - **Railway/Render**: Simple container deployment

2. **Configure Domain and SSL**:
   ```bash
   # Example: competition.yourschool.edu
   # Students access: https://competition.yourschool.edu
   ```

3. **Update Environment Variables**:
   ```env
   # Production settings
   SECRET_KEY=your-secure-random-string
   DATABASE_URL=postgresql://user:pass@host:5432/db
   REACT_APP_API_URL=https://competition.yourschool.edu
   ```

4. **Set up Reverse Proxy** (nginx example):
   ```nginx
   server {
       listen 80;
       server_name competition.yourschool.edu;
       return 301 https://$server_name$request_uri;
   }

   server {
       listen 443 ssl;
       server_name competition.yourschool.edu;
       
       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;
       
       location / {
           proxy_pass http://localhost:3000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
       
       location /api {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

5. **Enable HTTPS** with Let's Encrypt:
   ```bash
   sudo certbot --nginx -d competition.yourschool.edu
   ```

### Quick Deployment Options

**Option 1: Railway (Recommended for beginners)**
```bash
# 1. Fork this repository to your GitHub
# 2. Connect to Railway.app
# 3. Deploy automatically
# 4. Get public URL like: https://your-app.railway.app
```

**Option 2: DigitalOcean App Platform**
```bash
# 1. Push to GitHub
# 2. Connect DigitalOcean App Platform
# 3. Deploy with docker-compose.yml
# 4. Get public URL
```

**Option 3: AWS EC2**
```bash
# 1. Launch EC2 instance
# 2. Install Docker and Docker Compose
# 3. Clone repository
# 4. Run: docker-compose up -d
# 5. Configure security groups and domain
```

### Docker Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Update services
docker-compose pull
docker-compose up -d

# Backup database
docker-compose exec postgres pg_dump -U competition_user competition_db > backup.sql
```

## 🧪 Testing

### Manual Testing

1. **Student Workflow**:
   - Submit a Python solution for "Hello World"
   - Submit a C++ solution for "Sum of Two Numbers"
   - Check different error scenarios

2. **Teacher Workflow**:
   - Create a new problem with test cases
   - View submission analytics
   - Test GitHub integration (if configured)

### Automated Testing

```bash
# Run backend tests
docker-compose exec backend python -m pytest

# Run frontend tests
docker-compose exec frontend npm test
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Troubleshooting

### Common Issues

1. **Services not starting**:
   ```bash
   docker-compose logs
   docker-compose down
   docker-compose up --build
   ```

2. **Database connection issues**:
   ```bash
   docker-compose restart postgres
   docker-compose exec postgres psql -U competition_user -d competition_db
   ```

3. **Code execution failures**:
   ```bash
   docker-compose logs code-executor
   docker system prune -f
   ```

4. **GitHub integration not working**:
   - Verify your GitHub token has correct scopes
   - Check token expiration
   - Ensure repository permissions

### Getting Help

- Check the logs: `docker-compose logs -f`
- Review the API documentation: http://localhost:8000/docs
- Open an issue on GitHub with detailed error information

## 🔮 Future Enhancements

- [ ] Support for more programming languages (Java, JavaScript, etc.)
- [ ] Advanced plagiarism detection
- [ ] Real-time collaboration features
- [ ] Mobile app support
- [ ] Integration with learning management systems
- [ ] Advanced analytics and reporting
- [ ] Automated grading with AI assistance 