import streamlit as st
import os
import google.generativeai as genai
from dotenv import load_dotenv
import json
import re
import pandas as pd
from datetime import datetime
import pytz

# --- Load API Key ---
load_dotenv()
try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    API_KEY_CONFIGURED = True
except KeyError:
    API_KEY_CONFIGURED = False

# --- Constants ---
SEARCH_INTENT_KEYWORDS = ['bhk', 'flat', 'property', 'house', 'apartment', 'pune', 'mumbai', 'bangalore', 'chennai', 'delhi', 'hyderabad', 'cr', 'lakh', 'crore', 'lakhs', 'under', 'between', 'above', 'ready to move', 'possession']

# --- AI Logic Functions ---

def _parse_filters_from_query(chat_history):
    """Internal function to parse property filters from a query using Gemini."""
    if not API_KEY_CONFIGURED: return {}

    last_filters = next((msg.get('filters', {}) for msg in reversed(chat_history) if isinstance(msg, dict) and 'filters' in msg), {})
    formatted_history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history if isinstance(msg, dict)])

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
    
    prompt = f"""
    You are an expert real estate query parser. Your goal is to extract search filters from the user's latest message, using the conversation history and previous filters as context.

    **Previous Filters:** {json.dumps(last_filters)}
    **Conversation History:**
    {formatted_history}

    **Rules:**
    - From the LATEST user message, extract new information and merge it with previous filters.
    - Budget: "between X and Y Cr" -> budget_min_cr: X, budget_max_cr: Y. "under Y Cr" -> budget_max_cr: Y.
    - ALWAYS return a value for every field, using the previous filter's value if it hasn't changed.

    Call the `find_properties` function with the complete, updated set of filters.
    """
    
    try:
        model = genai.GenerativeModel(model_name="gemini-1.5-flash", tools=[EXTRACTION_SCHEMA])
        response = model.generate_content(prompt)
        
        if response.candidates and response.candidates[0].content.parts[0].function_call:
            raw_filters = response.candidates[0].content.parts[0].function_call.args
            sanitized_filters = {key: list(value) if hasattr(value, '__iter__') and not isinstance(value, str) else value for key, value in raw_filters.items()}
            print(f"[AI] Filters extracted: {json.dumps(sanitized_filters, indent=2)}")
            return sanitized_filters
    except Exception as e:
        st.error(f"An AI parsing error occurred: {e}")
    return {}


def _generate_search_summary(user_query, results_df):
    """Internal function to generate a summary for search results."""
    if not API_KEY_CONFIGURED or results_df.empty:
        return "Unfortunately, no properties matched your updated search criteria. Please try adjusting your filters."

    prompt = f"""
    A user asked: "{user_query}". I found some relevant properties. Here is a sample:
    {results_df.head(3).to_json(orient='records')}
    Write a 2-3 sentence summary. CRITICAL: Do NOT mention the total number of properties. Start with something like "Certainly, here are some properties that match your search."
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"[AI] Error during summarization: {e}")
    return "Here are the properties I found based on your search."


def _generate_general_response(chat_history):
    """
    Internal function to generate a conversational response for non-search queries.
    """
    if not API_KEY_CONFIGURED:
        return "I am a property search assistant. Please ask me about real estate."
        
    # Get current time for context
    ist = pytz.timezone('Asia/Kolkata')
    current_time = datetime.now(ist).strftime('%Y-%m-%d %I:%M %p')

    # Format history for the prompt
    formatted_history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history if isinstance(msg, dict)])

    prompt = f"""
    You are a friendly and helpful AI assistant for NoBroker.com, a real estate platform in India.
    Your primary function is to help users search for properties, but you can also make small talk.
    The current date and time in Pune, India is {current_time}.

    Keep your answers concise, polite, and helpful.
    If you don't know an answer, say so. Do not make up information.
    
    Conversation History:
    {formatted_history}
    
    Respond to the last user message.
    """
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"[AI] Error during general response generation: {e}")
    return "I'm sorry, I'm having trouble responding right now. Please try asking a property-related question."


def get_bot_response(chat_history, data_df):
    """
    This is the main "router" function.
    It classifies the user's intent and returns the appropriate response.
    """
    latest_query = chat_history[-1]['content'].lower()

    # --- Step 1: Intent Classification ---
    # Simple keyword-based intent classification.
    is_search_query = any(keyword in latest_query for keyword in SEARCH_INTENT_KEYWORDS)

    # If the user asks a follow-up that seems conversational but previous query was a search, assume it's a search refinement.
    if not is_search_query and len(chat_history) > 2:
        # Check if the second to last message was an assistant's search result
        if chat_history[-2]['role'] == 'assistant' and chat_history[-2].get('cards'):
             is_search_query = True

    # --- Step 2: Action based on Intent ---
    if is_search_query:
        print("[Router] Intent: property_search")
        filters = _parse_filters_from_query(chat_history)
        
        # Search the properties in the dataframe
        results_df = data_df.copy()
        if city := filters.get('city'):
            results_df = results_df[results_df['city_lower'] == city.lower()]
        if bhk_list := filters.get('bhk_list'):
            results_df = results_df[results_df['bhk'].isin([float(b) for b in bhk_list])]
        if budget_min := filters.get('budget_min_cr'):
            results_df = results_df[results_df['price_cr'] >= budget_min]
        if budget_max := filters.get('budget_max_cr'):
            results_df = results_df[results_df['price_cr'] <= budget_max]

        summary = _generate_search_summary(latest_query, results_df)
        cards = results_df.head(6).to_dict('records')
        
        return {
            "role": "assistant",
            "content": summary,
            "cards": cards,
            "filters": filters
        }
    else:
        print("[Router] Intent: general_conversation")
        response_text = _generate_general_response(chat_history)
        return {
            "role": "assistant",
            "content": response_text,
            "cards": [],
            "filters": {}
        }

