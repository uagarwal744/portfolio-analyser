"""Sidebar component for portfolio upload and summary."""

import httpx
import pandas as pd
import streamlit as st

API_URL = "http://localhost:8000/api"


def render_sidebar(session_id: str):
    """Render the sidebar with upload controls and portfolio summary."""
    with st.sidebar:
        st.title("📊 Portfolio Setup")
        
        # If we already have a portfolio, show summary and reset option
        if st.session_state.get("portfolio"):
            _render_portfolio_summary()
            if st.button("Reset Session", use_container_width=True, type="secondary"):
                st.session_state.clear()
                st.rerun()
            return

        st.markdown("Upload your portfolio to get started.")

        # Tabbed interface for File vs Text Paste
        tab1, tab2 = st.tabs(["Upload CSV", "Paste Text"])

        with tab1:
            uploaded_file = st.file_uploader(
                "Choose a CSV file",
                type="csv",
                help="Must contain columns: ticker, quantity, buy_price"
            )
            if uploaded_file is not None and st.button("Analyze File", use_container_width=True, type="primary"):
                _handle_file_upload(session_id, uploaded_file)

        with tab2:
            st.markdown("Paste comma-separated text:")
            default_text = "ticker,quantity,buy_price\nRELIANCE,50,2450\nTCS,30,3800\nHDFCBANK,100,1650"
            text_input = st.text_area("CSV Content", value=default_text, height=150)
            if st.button("Analyze Text", use_container_width=True, type="primary"):
                _handle_text_upload(session_id, text_input)


def _handle_file_upload(session_id: str, file):
    """Send uploaded file to FastAPI."""
    with st.spinner("Analyzing portfolio..."):
        try:
            files = {"file": (file.name, file.getvalue(), "text/csv")}
            data = {"session_id": session_id}
            
            with httpx.Client(timeout=60.0) as client:
                response = client.post(f"{API_URL}/portfolio/upload/file", data=data, files=files)
            
            _process_upload_response(response)
        except Exception as e:
            st.error(f"Connection error: {e}")


def _handle_text_upload(session_id: str, text: str):
    """Send pasted text to FastAPI."""
    with st.spinner("Analyzing portfolio..."):
        try:
            payload = {
                "session_id": session_id,
                "content": text
            }
            with httpx.Client(timeout=60.0) as client:
                response = client.post(f"{API_URL}/portfolio/upload/text", json=payload)
            
            _process_upload_response(response)
        except Exception as e:
            st.error(f"Connection error: {e}")


def _process_upload_response(response: httpx.Response):
    """Handle the API response from an upload."""
    if response.status_code == 200:
        data = response.json()
        if data.get("success"):
            # Update session state with the new portfolio data
            st.session_state["portfolio"] = data["portfolio"]
            # Add the initial summary message to chat
            if "messages" not in st.session_state:
                st.session_state["messages"] = []
            st.session_state["messages"].append({"role": "assistant", "content": data["message"]})
            st.rerun()
        else:
            st.error(data.get("error", "Failed to load portfolio"))
    else:
        st.error(f"Server error: {response.status_code}")


def _render_portfolio_summary():
    """Render the loaded portfolio summary in the sidebar."""
    portfolio = st.session_state["portfolio"]
    
    st.success("✅ Portfolio Loaded")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Invested", f"₹{portfolio['total_invested']:,.0f}")
    with col2:
        st.metric("Holdings", portfolio['num_holdings'])
        
    st.markdown("### Current Holdings")
    
    # Create a nice dataframe view
    df_data = []
    for h in portfolio["holdings"]:
        df_data.append({
            "Ticker": h["ticker"],
            "Qty": h["quantity"],
            "Sector": h["sector"] or "-",
            "Weight": f"{h['weight']*100:.1f}%"
        })
    
    df = pd.DataFrame(df_data)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Qty": st.column_config.NumberColumn(format="%d"),
        }
    )
