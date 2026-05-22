"""Launcher script to start both FastAPI and Streamlit."""

import os
import subprocess
import sys
import time


def main():
    """Start FastAPI and Streamlit processes."""
    print("🚀 Starting Portfolio Analyzer...")
    
    # Check if .env exists
    if not os.path.exists(".env"):
        print("⚠️ Warning: .env file not found. Ensure GEMINI_API_KEY is set.")
        
    env = os.environ.copy()
    
    # 1. Start FastAPI backend
    print("📦 Starting FastAPI backend on port 8000...")
    api_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "api.main:app", "--port", "8000", "--reload"],
        env=env
    )
    
    # Wait a moment for API to initialize
    time.sleep(2)
    
    if api_process.poll() is not None:
        print("❌ FastAPI backend failed to start. Exiting.")
        sys.exit(1)
        
    # 2. Start Streamlit frontend
    print("🎨 Starting Streamlit frontend on port 8501...")
    frontend_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "frontend/app.py"],
        env=env
    )
    
    try:
        # Keep main thread alive
        while True:
            time.sleep(1)
            # Check if either process died
            if api_process.poll() is not None:
                print("❌ FastAPI backend stopped unexpectedly.")
                frontend_process.terminate()
                break
            if frontend_process.poll() is not None:
                print("❌ Streamlit frontend stopped unexpectedly.")
                api_process.terminate()
                break
    except KeyboardInterrupt:
        print("\n🛑 Stopping services...")
        api_process.terminate()
        frontend_process.terminate()
        api_process.wait()
        frontend_process.wait()
        print("Goodbye! 👋")


if __name__ == "__main__":
    main()
