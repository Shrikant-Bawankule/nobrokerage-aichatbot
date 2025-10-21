import streamlit as st
import pandas as pd
import os
import google.generativeai as genai
from dotenv import load_dotenv
import json
import re

# --- 1. CONFIGURATION & SETUP ---

st.set_page_config(
    page_title="NoBroker AI Search",
    page_icon="🏠",
    layout="wide"
)

# Load environment variables for the API key
load_dotenv()
API_KEY_CONFIGURED = "GOOGLE_API_KEY" in os.environ
if API_KEY_CONFIGURED:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# --- 2. DATA & AI CORE FUNCTIONS ---

@st.cache_data(show_spinner="Loading property data...")
def load_data():
    """Loads and preprocesses the property dataset from a CSV file."""
    try:
        df = pd.read_csv('data/merged_property_dataset.csv')
        # Pre-process columns for efficient searching
        df['city_lower'] = df['city'].str.lower()
        df['status_lower'] = df['possession_status'].str.lower()
        
        for col in ['bhk', 'price_cr', 'pincode', 'balcony', 'bathrooms']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    except FileNotFoundError:
        st.error("`data/merged_property_dataset.csv` not found. Please follow the setup instructions in README.md.")
        return None

def parse_query_with_context(chat_history):
    """
    Uses the Gemini API to parse a user's query into structured search filters,
    maintaining the context of the conversation.
    """
    if not API_KEY_CONFIGURED:
        return {}

    # Find the most recent set of filters from the chat history for context
    last_filters = next((msg.get('filters', {}) for msg in reversed(st.session_state.get('messages', [])) if msg.get('filters')), {})
    
    formatted_history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])

    prompt = f"""
    You are an expert real estate query parser. Your goal is to extract search filters from the user's latest message, using the conversation history and previous filters as context.

    Previous Filters: {json.dumps(last_filters)}
    Conversation History:
    {formatted_history}

    Rules:
    - From the LATEST user message, extract new information.
    - If a user provides a new value (e.g., a new city), overwrite the old one.
    - If a user adds a new filter (e.g., a budget), add it to existing filters.
    - Budget: "between X and Y Cr" -> budget_min_cr: X, budget_max_cr: Y. "under Y Cr" -> budget_max_cr: Y.
    - ALWAYS return a value for every field, using the previous filter's value if it hasn't changed.

    Call the `find_properties` function with the complete, updated set of filters.
    """
    
    extraction_schema = {
        "name": "find_properties", "description": "Extracts filters for a property search.",
        "parameters": {
            "type": "OBJECT", "properties": {
                "city": {"type": "STRING"}, "bhk_list": {"type": "ARRAY", "items": {"type": "NUMBER"}},
                "budget_min_cr": {"type": "NUMBER"}, "budget_max_cr": {"type": "NUMBER"},
                "status_list": {"type": "ARRAY", "items": {"type": "STRING"}}
            }, "required": ["city", "bhk_list", "budget_min_cr", "budget_max_cr", "status_list"]
        }
    }

    try:
        model = genai.GenerativeModel(model_name="gemini-2.5-flash", tools=[extraction_schema])
        response = model.generate_content(prompt)
        
        if response.candidates and response.candidates[0].content.parts[0].function_call:
            raw_filters = response.candidates[0].content.parts[0].function_call.args
            
            # Sanitize the AI's response to prevent JSON serialization errors
            sanitized_filters = {}
            for key, value in raw_filters.items():
                sanitized_filters[key] = list(value) if hasattr(value, '__iter__') and not isinstance(value, str) else value
            return sanitized_filters
    except Exception as e:
        st.error(f"An error occurred with the AI model: {e}")
    return {}

def search_properties(df, filters):
    """Filters the master DataFrame based on the extracted criteria."""
    if df is None or not filters:
        return pd.DataFrame()
    
    results = df.copy()
    
    if city := filters.get('city'):
        results = results[results['city_lower'] == city.lower()]
    if bhk_list := filters.get('bhk_list'):
        results = results[results['bhk'].isin([float(b) for b in bhk_list])]
    if budget_min := filters.get('budget_min_cr'):
        results = results[results['price_cr'] >= budget_min]
    if budget_max := filters.get('budget_max_cr'):
        results = results[results['price_cr'] <= budget_max]
        
    return results

def generate_summary(user_query, results_df):
    """Generates a grounded, natural language summary of the search results."""
    if not API_KEY_CONFIGURED or results_df.empty:
        return "Here are the properties I found based on your search criteria."

    prompt = f"""
    A user asked: "{user_query}". I found some properties. Here is a sample:
    {results_df.head(3).to_json(orient='records')}
    Write a 2-3 sentence summary. CRITICAL: Do NOT mention the total number of properties found. Just describe what you see.
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Summary generation failed: {e}")
        return "Here are the properties I found based on your search."

# --- 3. UI COMPONENTS ---

def render_sidebar():
    """Renders the sidebar for navigation and actions."""
    with st.sidebar:
        st.title("Chat History")

        if st.button("Clear Chat History", use_container_width=True, type="primary"):
            st.session_state.clear()
            st.rerun()

def display_property_card(card_data, container):
    """Renders a single, detailed property card within a specified container."""
    with container:
        st.subheader(card_data.get('projectName', 'N/A'))
        st.caption(f"📍 {card_data.get('landmark', 'N/A')} | Pincode: {int(card_data.get('pincode', 0)) if pd.notna(card_data.get('pincode')) else 'N/A'}")
        st.markdown("---")

        sub_cols = st.columns(3)
        sub_cols[0].metric("Price", card_data.get('price_formatted', 'N/A'))
        sub_cols[1].metric("BHK", f"{int(card_data.get('bhk', 0))}")
        sub_cols[2].metric("Balconies", f"🌳 {int(card_data.get('balcony', 0))}")

        status = card_data.get('possession_status', 'N/A')
        if "Ready" in status:
            st.success(f"**Status:** {status}", icon="✅")
        else:
            st.warning(f"**Status:** {status}", icon="⏳")

# --- 4. MAIN APP FLOW ---

def main():
    """The main function that orchestrates the application flow."""
    render_sidebar()
    master_df = load_data()
    st.header("Chat With Your Real Estate Assistant")

    if not API_KEY_CONFIGURED and master_df is not None:
        st.error("Your Google AI API key is not configured. Please set the `GOOGLE_API_KEY` in your .env file.")
        st.stop()
    
    if master_df is None:
        st.stop()

    if "messages" not in st.session_state:
        st.session_state.messages = [{"role": "assistant", "content": "Hello! How can I help you find your dream home today?", "filters": {}}]

    # Display chat history
    for message in st.session_state.messages:
        avatar = "👤" if message["role"] == "user" else "🤖"
        with st.chat_message(message["role"], avatar=avatar):
            st.write(message["content"])
            if "cards" in message and message["cards"]:
                cols = st.columns(2)
                for i, card in enumerate(message["cards"]):
                    display_property_card(card, cols[i % 2])

    # Handle new user input
    if prompt := st.chat_input("e.g., '2BHK in Mumbai between 1 and 2cr'"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user", avatar="👤"):
            st.write(prompt)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking..."):
                filters = parse_query_with_context(st.session_state.messages)
                results_df = search_properties(master_df, filters)
                summary = generate_summary(prompt, results_df)
                cards_list = results_df.head(6).to_dict('records')
            
            st.write(summary)
            if cards_list:
                cols = st.columns(2)
                for i, card in enumerate(cards_list):
                    display_property_card(card, cols[i % 2])
            
            # Append the full response to the session state
            st.session_state.messages.append({
                "role": "assistant",
                "content": summary,
                "cards": cards_list,
                "filters": filters
            })

if __name__ == "__main__":
    main()

