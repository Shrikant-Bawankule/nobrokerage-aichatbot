import streamlit as st
import pandas as pd
import os
import google.generativeai as genai
from dotenv import load_dotenv
import json
import re
from datetime import datetime
import pytz

# --- Constants ---
API_KEY_CONFIGURED = "GOOGLE_API_KEY" in os.environ or "st.secrets" in st

# --- AI Configuration ---
if API_KEY_CONFIGURED:
    try:
        # Try to get key from Streamlit's secrets first
        api_key = st.secrets.get("GOOGLE_API_KEY", os.environ.get("GOOGLE_API_KEY"))
        genai.configure(api_key=api_key)
    except Exception as e:
        print(f"Error configuring Generative AI: {e}")
        API_KEY_CONFIGURED = False

# --- Data Loading and Preparation (More Robust) ---
@st.cache_data
def load_and_prep_data():
    """
    Loads, prepares, and caches the dataset from the /data folder.
    This version has improved error handling for deployment.
    """
    try:
        # --- THIS IS THE FIX ---
        # Build a reliable path to the data file.
        # This works both locally and on Streamlit Cloud.
        base_path = os.path.dirname(os.path.abspath(__file__))
        data_file_path = os.path.join(base_path, '..', 'data', 'merged_property_dataset.csv')
        
        df = pd.read_csv(data_file_path)
        
        # Standardize column names for consistency
        df['city_lower'] = df['city'].str.lower()
        df['status_lower'] = df['possession_status'].str.lower()
        
        for col in ['bhk', 'price_cr', 'pincode', 'balcony', 'bathrooms']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        print("Dataset loaded and prepared successfully.")
        return df
    except FileNotFoundError:
        # This error message will now appear in your Streamlit app if the file is missing
        st.error(
            "**Data file not found!** Please ensure you have a `/data` folder in your "
            "GitHub repository with `merged_property_dataset.csv` inside it."
        )
        return None
    except Exception as e:
        st.error(f"An error occurred while loading the data: {e}")
        return None

# (The rest of your ai_core.py file remains the same)
# ...
# The functions parse_query_with_context, generate_summary, etc. are unchanged.
# ...

