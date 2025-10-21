import os
import google.generativeai as genai
from dotenv import load_dotenv
import json
import re

# --- Load API Key ---
load_dotenv()
try:
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
except KeyError:
    # This will be handled by the Streamlit app's error message
    pass

# The schema now includes a minimum and maximum budget to handle ranges.
EXTRACTION_SCHEMA = {
    "name": "find_properties",
    "description": "Extracts filters for a property search from a user's natural language query and conversation history.",
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "city": {"type": "STRING", "description": "The city for the property search, e.g., 'Pune' or 'Mumbai'."},
            "bhk_list": {"type": "ARRAY", "items": {"type": "NUMBER"}, "description": "A list of BHK numbers, e.g., [2, 3]."},
            "budget_min_cr": {"type": "NUMBER", "description": "The MINIMUM budget in Crores. e.g., for 'between 1 and 2 Cr', this would be 1."},
            "budget_max_cr": {"type": "NUMBER", "description": "The MAXIMUM budget in Crores. e.g., for 'under 1.2 Cr' or 'between 1 and 2 Cr', this would be 2."},
            "status_list": {"type": "ARRAY", "items": {"type": "STRING"}, "description": "List of statuses, e.g., ['Ready to Move']."}
        },
        "required": ["city", "bhk_list", "budget_min_cr", "budget_max_cr", "status_list"]
    }
}


def parse_query_with_context(chat_history):
    """
    Uses Gemini to parse the latest user query, considering the entire conversation for context.
    Now correctly extracts budget ranges.
    """
    print(f"[AI] Parsing query with context...")
    
    # Format the history for the AI prompt
    formatted_history = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history if isinstance(msg, dict)])
    
    # Get the last known filters to provide more context
    last_filters = {}
    for i in range(len(chat_history) - 2, -1, -1):
        # Check if the message is a dictionary and has the 'filters' key
        if isinstance(chat_history[i], dict) and chat_history[i].get('filters'):
            last_filters = chat_history[i]['filters']
            break

    # This prompt is upgraded to handle budget ranges.
    prompt = f"""
    You are an expert at parsing real estate queries.
    Analyze the latest user query in the context of the conversation history and the last applied filters.
    Your goal is to call the `find_properties` function with the most accurate set of filters.

    **Rules for Budget:**
    - "between X and Y Cr" -> budget_min_cr: X, budget_max_cr: Y
    - "over X Cr" or "above X Cr" -> budget_min_cr: X, budget_max_cr: None
    - "under Y Cr" or "below Y Cr" -> budget_min_cr: None, budget_max_cr: Y
    - "X Lakhs" -> Convert to Crores (e.g., 80 Lakhs is 0.8 Cr)
    - If a previous budget exists and a new one is given, use the new one.

    **Last Applied Filters:** {json.dumps(last_filters)}
    **Conversation History:**
    {formatted_history}

    Based on the LATEST user message, update the filters and call the `find_properties` function.
    """

    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            tools=[EXTRACTION_SCHEMA]
        )
        response = model.generate_content(prompt)
        
        if response.candidates and response.candidates[0].content.parts[0].function_call:
            function_call = response.candidates[0].content.parts[0].function_call
            filters = {key: value for key, value in function_call.args.items()}
            print(f"[AI] Filters extracted: {json.dumps(filters, indent=2)}")
            return filters
        else:
            print("[AI] AI did not return a function call. Falling back.")
            return fallback_regex_parser(chat_history)

    except Exception as e:
        print(f"[AI] Error during parsing: {e}")
        return fallback_regex_parser(chat_history)


def fallback_regex_parser(chat_history):
    """A simple regex parser that now tries to understand ranges."""
    print("[AI] Using fallback regex parser.")
    latest_query = chat_history[-1]['content']
    
    range_match = re.search(r'between\s*([\d\.]+)\s*(?:and|-)\s*([\d\.]+)\s*cr', latest_query, re.IGNORECASE)
    under_match = re.search(r'(?:under|below)\s*([\d\.]+)\s*cr', latest_query, re.IGNORECASE)
    
    filters = {}
    if range_match:
        filters['budget_min_cr'] = float(range_match.group(1))
        filters['budget_max_cr'] = float(range_match.group(2))
    elif under_match:
        filters['budget_max_cr'] = float(under_match.group(1))
    
    print(f"[AI] Fallback filters: {json.dumps(filters, indent=2)}")
    return filters


def generate_summary(user_query, results_df):
    """
    Generates a grounded summary of the search results.
    This prompt is updated to NOT mention the total count to avoid the "trust issue".
    """
    if results_df.empty:
        return "Unfortunately, no properties matched your search criteria. Please try adjusting your filters."

    # The AI is now told NOT to mention the total count.
    prompt = f"""
    You are a helpful real estate assistant. A user asked: "{user_query}"
    I found some relevant properties in the database. Here is a sample:
    {results_df.head(3).to_json(orient='records')}

    Please write a 2-3 sentence summary of these findings.
    
    **CRITICAL RULE:** Do NOT mention the total number of properties found (e.g., "I found 18 properties").
    Instead, just describe the results you see. Start with something like "Based on your query, I found several properties that might interest you."
    """
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"[AI] Error during summarization: {e}")
        return "Here are the properties I found based on your search."

