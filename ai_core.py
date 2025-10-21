import os
import json
import re
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv

# --- SETUP & CONFIGURATION ---

load_dotenv()
API_KEY_CONFIGURED = "GOOGLE_API_KEY" in os.environ
if API_KEY_CONFIGURED:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

# --- DATA HANDLING ---

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
        # The main app will handle displaying the error to the user.
        return None

# --- AI & SEARCH LOGIC ---

def parse_query_with_context(chat_history, last_filters):
    """
    Uses the Gemini API to parse a user's query into structured search filters,
    maintaining the context of the conversation.
    """
    if not API_KEY_CONFIGURED:
        return {}

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
        print(f"AI parsing error: {e}")
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

