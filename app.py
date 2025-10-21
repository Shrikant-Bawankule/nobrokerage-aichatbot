import streamlit as st
import pandas as pd
import os
import google.generativeai as genai
from dotenv import load_dotenv
import json
import re

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="NoBroker AI Search", page_icon="🏠", layout="wide")

# --- 2. SETUP & API KEY ---
load_dotenv()
API_KEY_CONFIGURED = "GOOGLE_API_KEY" in os.environ
if API_KEY_CONFIGURED:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# --- 3. SIDEBAR ---
with st.sidebar:
    st.image("https://assets.nobroker.in/nb-new/public/Common/nobroker-logo.svg", width=200)
    st.title("AI-Powered Property Finder")
    st.info("This app understands follow-up questions to refine your search.")
    
    with st.expander("Example Conversation"):
        st.write("1. You: `2 bhk in pune`")
        st.write("2. You: `between 1 and 2 cr`")

    if st.button("Clear Chat History", use_container_width=True, type="primary"):
        st.session_state.messages = []
        st.rerun()

# --- 4. CORE LOGIC (DATA & AI) ---

@st.cache_data
def load_and_prep_data():
    """Loads, prepares, and caches the dataset. This is the foundation."""
    try:
        df = pd.read_csv('merged_property_dataset.csv')
        df['city_lower'] = df['city'].str.lower()
        df['status_lower'] = df['possession_status'].str.lower()
        
        for col in ['bhk', 'price_cr', 'pincode', 'balcony']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        st.success("Dataset loaded successfully!")
        return df
    except FileNotFoundError:
        st.error("`merged_property_dataset.csv` not found. Please place it in the project folder.")
        return None

def parse_query_with_context(chat_history):
    """
    Uses Gemini to parse the latest query, considering conversation context.
    This is the "understanding" part of the logic.
    """
    if not API_KEY_CONFIGURED: return {}

    last_filters = next((msg['filters'] for msg in reversed(st.session_state.messages) if msg.get('filters')), {})
    
    formatted_history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])

    prompt = f"""
    You are an expert real estate query parser. Your goal is to extract search filters from the user's latest message, using the conversation history and previous filters as context.

    **Previous Filters:** {json.dumps(last_filters)}
    **Conversation History:**
    {formatted_history}

    **Rules:**
    - From the LATEST user message, extract the new information.
    - If the user provides a new value for a filter, overwrite the old one.
    - If the user adds a new filter, add it to the existing filters.
    - Budget: "between X and Y Cr" -> budget_min_cr: X, budget_max_cr: Y. "under Y Cr" -> budget_max_cr: Y.
    - ALWAYS return a value for every field, using the previous filter's value if it hasn't changed.

    Call the `find_properties` function with the complete, updated set of filters.
    """
    
    EXTRACTION_SCHEMA = {
        "name": "find_properties", "description": "Extracts filters for a property search.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "city": {"type": "STRING"}, "bhk_list": {"type": "ARRAY", "items": {"type": "NUMBER"}},
                "budget_min_cr": {"type": "NUMBER"}, "budget_max_cr": {"type": "NUMBER"},
                "status_list": {"type": "ARRAY", "items": {"type": "STRING"}}
            },
            "required": ["city", "bhk_list", "budget_min_cr", "budget_max_cr", "status_list"]
        }
    }

    try:
        model = genai.GenerativeModel(model_name="gemini-2.5-flash", tools=[EXTRACTION_SCHEMA])
        response = model.generate_content(prompt)
        
        if response.candidates and response.candidates[0].content.parts[0].function_call:
            raw_filters = response.candidates[0].content.parts[0].function_call.args
            
            # --- THIS IS THE FIX ---
            # Sanitize the special AI object types into standard Python lists and dicts
            # This prevents the "RepeatedComposite is not JSON serializable" error.
            sanitized_filters = {}
            for key, value in raw_filters.items():
                # Check if it's an iterable (like the AI's list object) but not a string
                if hasattr(value, '__iter__') and not isinstance(value, str):
                    sanitized_filters[key] = list(value)
                else:
                    sanitized_filters[key] = value

            print(f"[AI] Filters extracted: {json.dumps(sanitized_filters, indent=2)}")
            return sanitized_filters
    except Exception as e:
        st.error(f"An error occurred with the AI model: {e}")
    return {}


def search_properties(df, filters):
    """This is the "fetching" part of the logic. It's now more robust."""
    if df is None or not filters: return pd.DataFrame()
    
    results = df.copy()
    print(f"[Search] Applying filters: {filters}")
    
    if city := filters.get('city'):
        results = results[results['city_lower'] == city.lower()]
    if bhk_list := filters.get('bhk_list'):
        results = results[results['bhk'].isin([float(b) for b in bhk_list])]
    if budget_min := filters.get('budget_min_cr'):
        results = results[results['price_cr'] >= budget_min]
    if budget_max := filters.get('budget_max_cr'):
        results = results[results['price_cr'] <= budget_max]
        
    print(f"[Search] Found {len(results)} matching properties.")
    return results


def generate_summary(user_query, results_df):
    """Generates a grounded summary of the search results."""
    if not API_KEY_CONFIGURED or results_df.empty:
        return "Here are the properties I found based on your search criteria."

    prompt = f"""
    A user asked: "{user_query}". I found some properties. Here is a sample:
    {results_df.head(3).to_json(orient='records')}
    Write a 2-3 sentence summary. CRITICAL: Do NOT mention the total number of properties. Just describe what you see.
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception:
        return "Here are the properties I found based on your search."

# --- 5. MAIN APP UI & INTERACTION ---
master_df = load_and_prep_data()
st.header("Chat With Your AI Property Assistant 💬")

if not API_KEY_CONFIGURED:
    st.error("Your Google AI API key is not configured. Please set the `GOOGLE_API_KEY` in your .env file.")
else:
    if "messages" not in st.session_state:
        st.session_state.messages = [{
            "role": "assistant", "content": "Hello! How can I help you find your dream home today?", "filters": {}
        }]

    for message in st.session_state.messages:
        avatar = "👤" if message["role"] == "user" else "🤖"
        with st.chat_message(message["role"], avatar=avatar):
            st.write(message["content"])
            if "cards" in message and message["cards"]:
                cols = st.columns(2)
                for i, card in enumerate(message["cards"]):
                    with cols[i % 2]:
                        with st.container(border=True):
                            st.subheader(card.get('projectName', 'N/A'))
                            st.caption(f"📍 {card.get('landmark', 'N/A')} | Pincode: {int(card.get('pincode', 0)) if pd.notna(card.get('pincode')) else 'N/A'}")
                            st.markdown("---")
                            sub_cols = st.columns(3)
                            sub_cols[0].metric("Price", card.get('price_formatted', 'N/A'))
                            sub_cols[1].metric("BHK", f"{int(card.get('bhk', 0))}")
                            sub_cols[2].metric("Balconies", f"🌳 {int(card.get('balcony', 0))}")
                            status = card.get('possession_status', 'N/A')
                            if "Ready" in status:
                                st.success(f"**Status:** {status}", icon="✅")
                            else:
                                st.warning(f"**Status:** {status}", icon="⏳")

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
                    with cols[i % 2]:
                        with st.container(border=True):
                            st.subheader(card.get('projectName', 'N/A'))
                            st.caption(f"📍 {card.get('landmark', 'N/A')} | Pincode: {int(card.get('pincode', 0)) if pd.notna(card.get('pincode')) else 'N/A'}")
                            st.markdown("---")
                            sub_cols = st.columns(3)
                            sub_cols[0].metric("Price", card.get('price_formatted', 'N/A'))
                            sub_cols[1].metric("BHK", f"{int(card.get('bhk', 0))}")
                            sub_cols[2].metric("Balconies", f"🌳 {int(card.get('balcony', 0))}")
                            status = card.get('possession_status', 'N/A')
                            if "Ready" in status:
                                st.success(f"**Status:** {status}", icon="✅")
                            else:
                                st.warning(f"**Status:** {status}", icon="⏳")
            
            st.session_state.messages.append({
                "role": "assistant",
                "content": summary,
                "cards": cards_list,
                "filters": filters
            })

