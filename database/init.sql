-- Database initialization script for Code Competition Platform

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Problems table
CREATE TABLE problems (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    difficulty VARCHAR(50) CHECK (difficulty IN ('easy', 'medium', 'hard')),
    time_limit INTEGER DEFAULT 30, -- seconds
    memory_limit INTEGER DEFAULT 512, -- MB
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

-- Test cases table
CREATE TABLE test_cases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    problem_id UUID REFERENCES problems(id) ON DELETE CASCADE,
    input_data TEXT NOT NULL,
    expected_output TEXT NOT NULL,
    is_hidden BOOLEAN DEFAULT false,
    points INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Submissions table
CREATE TABLE submissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    problem_id UUID REFERENCES problems(id) ON DELETE CASCADE,
    student_name VARCHAR(255) NOT NULL,
    student_email VARCHAR(255),
    language VARCHAR(20) NOT NULL CHECK (language IN ('python', 'cpp')),
    source_code TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'running', 'completed', 'error')),
    total_score INTEGER DEFAULT 0,
    total_points INTEGER DEFAULT 0,
    execution_time_ms INTEGER,
    memory_usage_mb INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Test results table
CREATE TABLE test_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    submission_id UUID REFERENCES submissions(id) ON DELETE CASCADE,
    test_case_id UUID REFERENCES test_cases(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL CHECK (status IN ('passed', 'failed', 'error', 'timeout')),
    actual_output TEXT,
    execution_time_ms INTEGER,
    memory_usage_mb INTEGER,
    error_message TEXT,
    points_earned INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Teachers table
CREATE TABLE teachers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- GitHub repositories table
CREATE TABLE github_repos (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    problem_id UUID REFERENCES problems(id) ON DELETE CASCADE,
    repo_name VARCHAR(255) NOT NULL,
    repo_url VARCHAR(500) NOT NULL,
    repo_owner VARCHAR(255) NOT NULL,
    access_token VARCHAR(500),
    branch VARCHAR(100) DEFAULT 'main',
    folder_structure TEXT,
    last_sync TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Student commits table
CREATE TABLE student_commits (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    github_repo_id UUID REFERENCES github_repos(id) ON DELETE CASCADE,
    student_name VARCHAR(255) NOT NULL,
    student_email VARCHAR(255),
    commit_hash VARCHAR(100) NOT NULL,
    commit_message TEXT NOT NULL,
    commit_date TIMESTAMP NOT NULL,
    files_changed TEXT,
    code_content TEXT,
    language VARCHAR(20),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'evaluated', 'error')),
    total_score INTEGER DEFAULT 0,
    total_points INTEGER DEFAULT 0,
    execution_time_ms INTEGER,
    memory_usage_mb INTEGER,
    error_message TEXT,
    evaluated_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Commit test results table
CREATE TABLE commit_test_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    student_commit_id UUID REFERENCES student_commits(id) ON DELETE CASCADE,
    test_case_id UUID REFERENCES test_cases(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL CHECK (status IN ('passed', 'failed', 'error', 'timeout')),
    actual_output TEXT,
    execution_time_ms INTEGER,
    memory_usage_mb INTEGER,
    error_message TEXT,
    points_earned INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better performance
CREATE INDEX idx_submissions_problem_id ON submissions(problem_id);
CREATE INDEX idx_submissions_student_email ON submissions(student_email);
CREATE INDEX idx_submissions_created_at ON submissions(created_at);
CREATE INDEX idx_test_results_submission_id ON test_results(submission_id);
CREATE INDEX idx_test_cases_problem_id ON test_cases(problem_id);
CREATE INDEX idx_github_repos_problem_id ON github_repos(problem_id);
CREATE INDEX idx_student_commits_repo_id ON student_commits(github_repo_id);
CREATE INDEX idx_student_commits_hash ON student_commits(commit_hash);
CREATE INDEX idx_commit_test_results_commit_id ON commit_test_results(student_commit_id);

-- Create a function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for tables with updated_at
CREATE TRIGGER update_problems_updated_at BEFORE UPDATE ON problems
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_github_repos_updated_at BEFORE UPDATE ON github_repos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert sample data
INSERT INTO problems (title, description, difficulty, time_limit, memory_limit) VALUES
('Hello World', 'Write a program that prints "Hello, World!" to the console.', 'easy', 5, 128),
('Sum of Two Numbers', 'Write a program that takes two integers as input and prints their sum.', 'easy', 10, 256),
('Fibonacci Sequence', 'Write a program that prints the first n numbers of the Fibonacci sequence.', 'medium', 15, 512),
('Sort Array', 'Write a program that sorts an array of integers in ascending order.', 'medium', 20, 512),
('Prime Number Check', 'Write a program that checks if a given number is prime.', 'hard', 30, 1024);

-- Insert sample test cases
INSERT INTO test_cases (problem_id, input_data, expected_output, is_hidden, points) VALUES
((SELECT id FROM problems WHERE title = 'Hello World'), '', 'Hello, World!', false, 10),
((SELECT id FROM problems WHERE title = 'Sum of Two Numbers'), '5 3', '8', false, 10),
((SELECT id FROM problems WHERE title = 'Sum of Two Numbers'), '10 20', '30', false, 10),
((SELECT id FROM problems WHERE title = 'Sum of Two Numbers'), '-5 8', '3', true, 10),
((SELECT id FROM problems WHERE title = 'Fibonacci Sequence'), '5', '0 1 1 2 3', false, 20),
((SELECT id FROM problems WHERE title = 'Fibonacci Sequence'), '8', '0 1 1 2 3 5 8 13', true, 20),
((SELECT id FROM problems WHERE title = 'Sort Array'), '5\n3 1 4 1 5', '1 1 3 4 5', false, 25),
((SELECT id FROM problems WHERE title = 'Sort Array'), '3\n9 8 7', '7 8 9', true, 25),
((SELECT id FROM problems WHERE title = 'Prime Number Check'), '7', 'true', false, 15),
((SELECT id FROM problems WHERE title = 'Prime Number Check'), '4', 'false', false, 15),
((SELECT id FROM problems WHERE title = 'Prime Number Check'), '17', 'true', true, 20);

-- Insert sample teacher (password: teacher123)
INSERT INTO teachers (username, password_hash, email) VALUES
('admin', '$2b$12$ti6TUhqPtHMnEpRpZWqrr.BLDU0y9kvtkJshEHJeXqjVHKm7OsgvG', 'admin@competition.com');
