#!/usr/bin/env python3
"""
Code Execution Service
Handles code evaluation requests from the main backend
"""

import os
import sys
import json
import time
import tempfile
import subprocess
import docker
from typing import Dict, Any

class CodeExecutionService:
    def __init__(self):
        self.client = docker.from_env()
        self.max_execution_time = int(os.getenv("MAX_EXECUTION_TIME", 30))
        self.max_memory = os.getenv("MAX_MEMORY", "512m")
        self.max_cpu = float(os.getenv("MAX_CPU", "1.0"))
        
    def execute_python(self, source_code: str, input_data: str, submission_id: str) -> Dict[str, Any]:
        """Execute Python code in a Docker container"""
        container_name = f"python_exec_{submission_id}_{int(time.time())}"
        
        # Create temporary directory for the code
        with tempfile.TemporaryDirectory() as temp_dir:
            # Write source code to file
            code_file = os.path.join(temp_dir, "solution.py")
            with open(code_file, "w") as f:
                f.write(source_code)
            
            # Write input data to file
            input_file = os.path.join(temp_dir, "input.txt")
            with open(input_file, "w") as f:
                f.write(input_data)
            
            try:
                # Run container
                container = self.client.containers.run(
                    "python:3.11-slim",
                    command=f"timeout {self.max_execution_time} python solution.py < input.txt",
                    volumes={
                        temp_dir: {
                            'bind': '/workspace',
                            'mode': 'ro'
                        }
                    },
                    working_dir="/workspace",
                    mem_limit=self.max_memory,
                    cpu_period=100000,
                    cpu_quota=int(100000 * self.max_cpu),
                    detach=True,
                    name=container_name,
                    remove=True,
                    network_disabled=True,
                    security_opt=['no-new-privileges'],
                    cap_drop=['ALL']
                )
                
                # Wait for completion
                start_time = time.time()
                result = container.wait(timeout=self.max_execution_time + 5)
                execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                
                # Get output
                output = container.logs(stdout=True, stderr=False).decode('utf-8').strip()
                error = container.logs(stderr=True, stdout=False).decode('utf-8').strip()
                
                # Get container stats
                stats = container.stats(stream=False)
                memory_usage = stats['memory_stats']['usage'] / (1024 * 1024)  # Convert to MB
                
                return {
                    "status": "completed" if result['StatusCode'] == 0 else "error",
                    "output": output,
                    "error": error if error else None,
                    "execution_time_ms": int(execution_time),
                    "memory_usage_mb": int(memory_usage),
                    "exit_code": result['StatusCode']
                }
                
            except docker.errors.ContainerError as e:
                return {
                    "status": "error",
                    "output": "",
                    "error": str(e),
                    "execution_time_ms": 0,
                    "memory_usage_mb": 0,
                    "exit_code": -1
                }
            except Exception as e:
                return {
                    "status": "error",
                    "output": "",
                    "error": str(e),
                    "execution_time_ms": 0,
                    "memory_usage_mb": 0,
                    "exit_code": -1
                }
    
    def execute_cpp(self, source_code: str, input_data: str, submission_id: str) -> Dict[str, Any]:
        """Execute C++ code in a Docker container"""
        container_name = f"cpp_exec_{submission_id}_{int(time.time())}"
        
        # Create temporary directory for the code
        with tempfile.TemporaryDirectory() as temp_dir:
            # Write source code to file
            code_file = os.path.join(temp_dir, "solution.cpp")
            with open(code_file, "w") as f:
                f.write(source_code)
            
            # Write input data to file
            input_file = os.path.join(temp_dir, "input.txt")
            with open(input_file, "w") as f:
                f.write(input_data)
            
            try:
                # Run container with compilation and execution
                container = self.client.containers.run(
                    "gcc:11",
                    command=f"bash -c 'g++ -std=c++17 -O2 solution.cpp -o solution && timeout {self.max_execution_time} ./solution < input.txt'",
                    volumes={
                        temp_dir: {
                            'bind': '/workspace',
                            'mode': 'rw'
                        }
                    },
                    working_dir="/workspace",
                    mem_limit=self.max_memory,
                    cpu_period=100000,
                    cpu_quota=int(100000 * self.max_cpu),
                    detach=True,
                    name=container_name,
                    remove=True,
                    network_disabled=True,
                    security_opt=['no-new-privileges'],
                    cap_drop=['ALL']
                )
                
                # Wait for completion
                start_time = time.time()
                result = container.wait(timeout=self.max_execution_time + 10)
                execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
                
                # Get output
                output = container.logs(stdout=True, stderr=False).decode('utf-8').strip()
                error = container.logs(stderr=True, stdout=False).decode('utf-8').strip()
                
                # Get container stats
                stats = container.stats(stream=False)
                memory_usage = stats['memory_stats']['usage'] / (1024 * 1024)  # Convert to MB
                
                return {
                    "status": "completed" if result['StatusCode'] == 0 else "error",
                    "output": output,
                    "error": error if error else None,
                    "execution_time_ms": int(execution_time),
                    "memory_usage_mb": int(memory_usage),
                    "exit_code": result['StatusCode']
                }
                
            except docker.errors.ContainerError as e:
                return {
                    "status": "error",
                    "output": "",
                    "error": str(e),
                    "execution_time_ms": 0,
                    "memory_usage_mb": 0,
                    "exit_code": -1
                }
            except Exception as e:
                return {
                    "status": "error",
                    "output": "",
                    "error": str(e),
                    "execution_time_ms": 0,
                    "memory_usage_mb": 0,
                    "exit_code": -1
                }
    
    def execute_code(self, source_code: str, language: str, input_data: str, submission_id: str) -> Dict[str, Any]:
        """Execute code based on language"""
        if language.lower() == "python":
            return self.execute_python(source_code, input_data, submission_id)
        elif language.lower() == "cpp":
            return self.execute_cpp(source_code, input_data, submission_id)
        else:
            return {
                "status": "error",
                "output": "",
                "error": f"Unsupported language: {language}",
                "execution_time_ms": 0,
                "memory_usage_mb": 0,
                "exit_code": -1
            }

def main():
    """Main function for the code execution service"""
    service = CodeExecutionService()
    
    # Simple test
    print("Code Execution Service started")
    print(f"Max execution time: {service.max_execution_time}s")
    print(f"Max memory: {service.max_memory}")
    print(f"Max CPU: {service.max_cpu}")
    
    # Keep the service running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Service stopped")

if __name__ == "__main__":
    main() 