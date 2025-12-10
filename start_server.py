#!/usr/bin/env python3
"""
Start the FastAPI development server
Usage: python start_server.py
"""

import subprocess
import sys
from pathlib import Path

def main():
    # Get the project root directory
    project_root = Path(__file__).parent
    
    # Ensure required directories exist
    (project_root / "temp_uploads").mkdir(exist_ok=True)
    (project_root / "redacted_outputs").mkdir(exist_ok=True)
    (project_root / "monitoring" / "prometheus").mkdir(parents=True, exist_ok=True)
    (project_root / "monitoring" / "grafana" / "provisioning" / "datasources").mkdir(parents=True, exist_ok=True)
    (project_root / "monitoring" / "grafana" / "provisioning" / "dashboards").mkdir(parents=True, exist_ok=True)
    
    # Get the virtual environment python executable
    if sys.platform == "win32":
        python_exe = project_root / ".venv" / "Scripts" / "python.exe"
    else:
        python_exe = project_root / ".venv" / "bin" / "python"
    
    # Check if virtual environment exists
    if not python_exe.exists():
        print("Virtual environment not found!")
        print("Please run: python -m venv .venv")
        return 1
    
    # Start uvicorn server
    # Prefer stable, local-only server defaults
    host = "127.0.0.1"
    port = "8000"
    # Build command with options
    cmd = [
        str(python_exe), "-m", "uvicorn",
        "app.main:app",
        "--host", host,
        "--port", port,
        "--log-level", "info",
        "--reload"  # Enable auto-reload for development
    ]
    
    print("Starting FastAPI server...")
    print(f"Server will be available at: http://{host}:{port}")
    print(f"API documentation: http://{host}:{port}/docs")
    print("Press Ctrl+C to stop the server")
    
    try:
        subprocess.run(cmd, cwd=project_root)
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except FileNotFoundError:
        print("Error: uvicorn not installed. Run: pip install uvicorn")
        return 1

if __name__ == "__main__":
    sys.exit(main())