import streamlit as st
import pandas as pd
import os
from ai_core import get_bot_response # Import the main router function from your AI core

# --- 1. Page Configuration & Constants ---
st.set_page_config(
    page_title="NoBroker AI Search",
    page_icon="🏠",
    layout="wide"
)
ASSISTANT_AVATAR = "🤖"
USER_AVATAR = "👤"

# --- 2. Data Loading ---
@st.cache_data(show_spinner="Loading property data...")
def load_data():
    """Loads and prepares the dataset from a CSV file."""
    try:
        df = pd.read_csv('merged_property_dataset.csv')
        # Pre-process columns for faster, case-insensitive searching
        df['city_lower'] = df['city'].str.lower()
        df['status_lower'] = df['possession_status'].str.lower()
        for col in ['bhk', 'price_cr', 'pincode', 'balcony', 'bathrooms']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    except FileNotFoundError:
        st.error("`merged_property_dataset.csv` not found. Please place it in the project folder.")
        return None

# --- 3. UI Components ---
def render_sidebar():
    """Renders the sidebar UI elements."""
    with st.sidebar:
        st.title("Chat History")
        

        if st.button("Clear Chat History", use_container_width=True, type="primary"):
            # Clear all session state to prevent errors
            st.session_state.clear()
            st.rerun()

def render_property_card(card_data, container):
    """Renders a single, detailed property card inside a given container."""
    with container:
        st.subheader(card_data.get('projectName', 'N/A'))
        
        caption_parts = []
        if landmark := card_data.get('landmark'):
            caption_parts.append(f"Near {landmark}")
        if pincode := card_data.get('pincode'):
            caption_parts.append(f"Pincode: {int(pincode) if pd.notna(pincode) else 'N/A'}")
        st.caption(f"📍 {' | '.join(caption_parts)}")

        st.markdown("---")
        
        sub_cols = st.columns(3)
        sub_cols[0].metric("Price", card_data.get('price_formatted', 'N/A'))
        sub_cols[1].metric("BHK", f"{int(card_data.get('bhk', 0))}")
        sub_cols[2].metric("Balconies", f" {int(card_data.get('balcony', 0))}")
        
        status = card_data.get('possession_status', 'N/A')
        if "Ready" in status:
            st.success(f"**Status:** {status}", icon="✅")
        else:
            st.warning(f"**Status:** {status}", icon="⏳")

def render_chat_history():
    """Displays the entire chat history from session_state."""
    for message in st.session_state.get('messages', []):
        avatar = USER_AVATAR if message["role"] == "user" else ASSISTANT_AVATAR
        with st.chat_message(message["role"], avatar=avatar):
            st.write(message["content"])
            # Display cards if they exist for this message
            if "cards" in message and message["cards"]:
                cols = st.columns(2)
                for i, card in enumerate(message["cards"]):
                    render_property_card(card, cols[i % 2])

# --- 4. Main Application Flow ---
def main():
    """The main function that runs the Streamlit application."""
    render_sidebar()
    master_df = load_data()
    
    st.header("Chat With Your AI Property Assistant 💬")

    if master_df is None:
        st.warning("Data could not be loaded. The application cannot proceed.")
        return

    # Initialize session state for messages
    if 'messages' not in st.session_state:
        st.session_state.messages = [{
            "role": "assistant",
            "content": "Hello! How can I help you find your dream home today?",
        }]
    
    render_chat_history()

    if prompt := st.chat_input("Ask about properties or just say hello..."):
        # Add user message to history
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user", avatar=USER_AVATAR):
            st.write(prompt)

        # Get the bot's response (which could be a search result or a chat message)
        with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
            with st.spinner("Thinking..."):
                # Pass the complete history and dataframe to the AI core
                bot_response = get_bot_response(st.session_state.messages, master_df)
            
            st.write(bot_response["content"])
            if bot_response.get("cards"):
                cols = st.columns(2)
                for i, card in enumerate(bot_response["cards"]):
                    render_property_card(card, cols[i % 2])
        
        # Add the complete bot response to history for context in the next turn
        st.session_state.messages.append(bot_response)

if __name__ == "__main__":
    main()

