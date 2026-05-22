"""Custom CSS styles for the Streamlit frontend."""

import streamlit as st


def apply_custom_styles():
    """Inject custom CSS to enhance the Streamlit UI."""
    st.markdown(
        """
        <style>
        /* Main layout tweaks */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 95%;
        }
        
        /* Chat container styling */
        .stChatMessage {
            background-color: transparent;
        }
        
        /* Predefined prompt buttons styling */
        div.stButton > button {
            width: 100%;
            border-radius: 20px;
            border: 1px solid #e0e0e0;
            background-color: #f8f9fa;
            color: #333;
            transition: all 0.2s ease-in-out;
        }
        
        div.stButton > button:hover {
            border-color: #0066cc;
            background-color: #e6f2ff;
            color: #0066cc;
        }
        
        /* Dashboard metric cards */
        div[data-testid="stMetricValue"] {
            font-size: 1.8rem;
        }
        
        /* Headers */
        h1, h2, h3 {
            font-family: 'Inter', 'Roboto', sans-serif;
            font-weight: 600;
        }
        
        /* Sidebar layout */
        section[data-testid="stSidebar"] {
            width: 350px !important;
            background-color: #262730;
        }
        
        /* Alert boxes (for concentration warnings, etc.) */
        .stAlert {
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        /* Hide default Streamlit elements */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        </style>
        """,
        unsafe_allow_html=True,
    )
