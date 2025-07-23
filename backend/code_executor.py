import docker
import os
import tempfile
import time
import json
from typing import Dict, Any, Optional
import subprocess
import shutil

class CodeExecutor:
    def __init__(self):
        try:
            # Set environment variable to use Unix socket
            os.environ['DOCKER_HOST'] = 'unix://var/run/docker.sock'
            self.client = docker.from_env()
            print("Docker connection successful")
        except Exception as e:
            print(f"Failed to connect to Docker: {e}")
            print("Using mock code execution for testing")
            self.client = None
        self.max_execution_time = int(os.getenv("MAX_EXECUTION_TIME", 30))
        self.max_memory = os.getenv("MAX_MEMORY", "512m")
        self.max_cpu = float(os.getenv("MAX_CPU", "1.0"))
        
    def execute_python(self, source_code: str, input_data: str, submission_id: str) -> Dict[str, Any]:
        """Execute Python code in a Docker container"""
        if not self.client:
            return self._mock_execute_python(source_code, input_data)
            
        container_name = f"python_exec_{submission_id}"
        
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
        if not self.client:
            return self._mock_execute_cpp(source_code, input_data)
            
        container_name = f"cpp_exec_{submission_id}"
        
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
    
    def cleanup_containers(self):
        """Clean up any running containers"""
        if not self.client:
            return
        try:
            containers = self.client.containers.list(filters={"name": "python_exec_"})
            for container in containers:
                container.stop(timeout=1)
                container.remove()
        except Exception:
            pass
        
        try:
            containers = self.client.containers.list(filters={"name": "cpp_exec_"})
            for container in containers:
                container.stop(timeout=1)
                container.remove()
        except Exception:
            pass

    def _mock_execute_python(self, source_code: str, input_data: str) -> Dict[str, Any]:
        """Mock Python execution for testing when Docker is not available"""
        import subprocess
        import tempfile
        import time
        
        try:
            # Create temporary files
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as code_file:
                code_file.write(source_code)
                code_file_path = code_file.name
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as input_file:
                input_file.write(input_data)
                input_file_path = input_file.name
            
            # Execute Python code
            start_time = time.time()
            result = subprocess.run(
                ['python3', code_file_path],
                input=input_data,
                capture_output=True,
                text=True,
                timeout=self.max_execution_time
            )
            execution_time = (time.time() - start_time) * 1000
            
            # Clean up temporary files
            import os
            os.unlink(code_file_path)
            os.unlink(input_file_path)
            
            return {
                "status": "completed" if result.returncode == 0 else "error",
                "output": result.stdout.strip(),
                "error": result.stderr.strip() if result.stderr else None,
                "execution_time_ms": int(execution_time),
                "memory_usage_mb": 50,  # Mock memory usage
                "exit_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "output": "",
                "error": "Execution timeout",
                "execution_time_ms": self.max_execution_time * 1000,
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

    def _mock_execute_cpp(self, source_code: str, input_data: str) -> Dict[str, Any]:
        """Mock C++ execution for testing when Docker is not available"""
        import subprocess
        import tempfile
        import time
        import os
        
        try:
            # Create temporary files
            with tempfile.NamedTemporaryFile(mode='w', suffix='.cpp', delete=False) as code_file:
                code_file.write(source_code)
                code_file_path = code_file.name
            
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as input_file:
                input_file.write(input_data)
                input_file_path = input_file.name
            
            # Compile C++ code
            executable_path = code_file_path + '.exe'
            compile_result = subprocess.run(
                ['g++', '-std=c++17', '-O2', code_file_path, '-o', executable_path],
                capture_output=True,
                text=True
            )
            
            if compile_result.returncode != 0:
                return {
                    "status": "error",
                    "output": "",
                    "error": f"Compilation error: {compile_result.stderr}",
                    "execution_time_ms": 0,
                    "memory_usage_mb": 0,
                    "exit_code": compile_result.returncode
                }
            
            # Execute compiled code
            start_time = time.time()
            result = subprocess.run(
                [executable_path],
                input=input_data,
                capture_output=True,
                text=True,
                timeout=self.max_execution_time
            )
            execution_time = (time.time() - start_time) * 1000
            
            # Clean up temporary files
            os.unlink(code_file_path)
            os.unlink(input_file_path)
            os.unlink(executable_path)
            
            return {
                "status": "completed" if result.returncode == 0 else "error",
                "output": result.stdout.strip(),
                "error": result.stderr.strip() if result.stderr else None,
                "execution_time_ms": int(execution_time),
                "memory_usage_mb": 50,  # Mock memory usage
                "exit_code": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "output": "",
                "error": "Execution timeout",
                "execution_time_ms": self.max_execution_time * 1000,
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