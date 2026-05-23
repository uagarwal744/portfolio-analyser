"""Chat interface component."""

import httpx
import streamlit as st

API_URL = "http://localhost:8000/api"

PREDEFINED_PROMPTS = [
    "What's my overall risk profile?",
    "Show me sector exposure",
    "How does my portfolio compare to Nifty 50?",
    "Run a tail risk analysis",
    "Check correlation between holdings",
    "Any hidden concentration risks?",
]


def render_chat(session_id: str):
    """Render the chat history, input, and suggestion buttons."""
    
    # Render chat history
    messages = st.session_state.get("messages", [])
    
    if len(messages) > 2:
        with st.expander("Previous Conversation", expanded=False):
            for msg in messages[:-2]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
        
        for msg in messages[-2:]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
    else:
        for msg in messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
            
    # Quick actions/suggestions (only show if portfolio is loaded)
    if st.session_state.get("portfolio"):
        suggestions = st.session_state.get("suggestions", PREDEFINED_PROMPTS[:4])
        if suggestions:
            st.markdown("---")
            st.markdown("<small>💡 **Suggested analyses:**</small>", unsafe_allow_html=True)
            
            # First row: up to 3 suggestions
            row1 = suggestions[:3]
            cols1 = st.columns(len(row1))
            for i, suggestion in enumerate(row1):
                with cols1[i]:
                    if st.button(suggestion, key=f"sugg_{i}", use_container_width=True):
                        _handle_chat(session_id, suggestion)
            
            # Second row: remaining suggestions
            row2 = suggestions[3:5]
            if row2:
                cols2 = st.columns(len(row2))
                for i, suggestion in enumerate(row2):
                    with cols2[i]:
                        if st.button(suggestion, key=f"sugg_{i+3}", use_container_width=True):
                            _handle_chat(session_id, suggestion)

    # Chat input
    if prompt := st.chat_input("Ask about your portfolio..."):
        _handle_chat(session_id, prompt)


def _handle_chat(session_id: str, message: str):
    """Send a user message to the FastAPI backend."""
    # Append user message immediately
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
        
    st.session_state["messages"].append({"role": "user", "content": message})
    
    # We must rerun to show the user message immediately, but we need a way to 
    # trigger the API call. Streamlit pattern: use a flag in session state.
    st.session_state["pending_chat"] = message
    st.rerun()


def process_pending_chat(session_id: str):
    """Process any pending chat messages (called from main app flow)."""
    if message := st.session_state.get("pending_chat"):
        # Clear the flag
        del st.session_state["pending_chat"]
        
        with st.chat_message("user"):
            pass # Already rendered in history loop
            
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                try:
                    payload = {
                        "session_id": session_id,
                        "message": message
                    }
                    with httpx.Client(timeout=120.0) as client:
                        response = client.post(f"{API_URL}/chat", json=payload)
                    
                    if response.status_code == 200:
                        data = response.json()
                        ai_msg = data["message"]
                        
                        # Display message
                        st.markdown(ai_msg)
                        
                        # Update session state
                        st.session_state["messages"].append({"role": "assistant", "content": ai_msg})
                        st.session_state["dashboard_signals"] = data.get("dashboard_signals", [])
                        
                        if data.get("suggested_questions"):
                            st.session_state["suggestions"] = data["suggested_questions"]
                            
                    else:
                        st.error(f"Error: {response.status_code}")
                except Exception as e:
                    st.error(f"Connection error: {e}")
                    
        # Rerun to update dashboard on the right side
        st.rerun()
