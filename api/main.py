"""FastAPI application entry point."""

import os
import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Add src to path so portfolio_analyzer is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

load_dotenv()

from api.routes import router

app = FastAPI(
    title="Portfolio Analyzer API",
    description="API for the LangGraph-based portfolio analyzer",
    version="0.1.0",
)

# Enable CORS for Streamlit frontend (default port 8501)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

@app.get("/health")
def health_check():
    """Simple health check endpoint."""
    return {"status": "ok"}
