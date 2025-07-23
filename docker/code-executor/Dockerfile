FROM ubuntu:22.04

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    g++ \
    gcc \
    make \
    time \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for running code
RUN useradd -m -s /bin/bash coderunner

# Set up working directory
WORKDIR /app

# Copy the code execution script
COPY code_executor.py .

# Make the script executable
RUN chmod +x code_executor.py

# Switch to non-root user
USER coderunner

# Expose port (if needed for health checks)
EXPOSE 8080

# Run the code executor
CMD ["python3", "code_executor.py"] 