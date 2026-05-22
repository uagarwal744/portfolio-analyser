"""Main Streamlit application."""

import os
import sys
import uuid

import streamlit as st

# Add the project root to the path so we can import local modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from frontend.components.chat import process_pending_chat, render_chat
from frontend.components.dashboard import render_dashboard
from frontend.components.sidebar import render_sidebar
from frontend.styles import apply_custom_styles

st.set_page_config(
    page_title="Portfolio Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


def init_session():
    """Initialize session state variables."""
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = str(uuid.uuid4())
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    if "dashboard_signals" not in st.session_state:
        st.session_state["dashboard_signals"] = []
    if "portfolio" not in st.session_state:
        st.session_state["portfolio"] = None


def main():
    apply_custom_styles()
    init_session()
    
    session_id = st.session_state["session_id"]
    
    # ── Sidebar (Upload & Summary) ──
    render_sidebar(session_id)
    
    # ── Main Content Area ──
    st.title("📊 Portfolio Analyzer")
    
    if not st.session_state.get("portfolio"):
        st.info("👈 Please upload your portfolio CSV in the sidebar to begin analysis.")
        return
        
    # Split layout: 45% Chat, 55% Dashboard
    col_chat, col_dash = st.columns([0.45, 0.55], gap="large")
    
    with col_chat:
        render_chat(session_id)
        # Process API call if a message was just sent
        process_pending_chat(session_id)
        
    with col_dash:
        render_dashboard(st.session_state.get("dashboard_signals", []))


if __name__ == "__main__":
    main()
