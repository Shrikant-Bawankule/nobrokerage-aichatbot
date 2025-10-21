# nobrokerage-aichatbot
AI-powered chat interface for NoBrokerage.com property search


NoBroker.com AI-Powered Property Search

This project is an intelligent, conversational chat interface built with Streamlit and Google Gemini. It allows users to search for properties using natural language queries, understands follow-up questions to refine the search, and displays results in a clean, user-friendly interface.

Live Demo: [Link to your deployed Streamlit App will go here]

🎯 Core Features

Natural Language Understanding: Parses complex queries like "2BHK in Pune between 1 and 2 Cr" to extract precise search filters.

Conversational Context: Remembers the previous search to understand follow-up questions (e.g., after asking for "flats in Mumbai," a follow-up of "under 3 Cr" refines the original search).

Dynamic Data Search: Filters a local CSV dataset in real-time using Pandas.

AI-Generated Summaries: Uses the Gemini API to provide helpful, grounded summaries of the search results without revealing sensitive counts.

Polished UI: A clean, attractive interface built with Streamlit, featuring a sidebar and appealing, component-based property cards.

⚙️ Tech Stack

Layer

Tool

Justification

App

Streamlit

Chosen for its speed in building interactive, data-centric web apps directly in Python.

AI / NLP

Google Gemini API (gemini-1.5-flash)

A powerful LLM used for its advanced function-calling (filter extraction) and text generation capabilities.

Data

Pandas DataFrame

The ideal choice for loading and filtering the provided CSV data efficiently in memory.

Language

Python

The industry standard for AI and data science, allowing for seamless integration of all components.

🚀 How to Run Locally

1. Clone the Repository

git clone [your-github-repo-url]
cd [your-repo-name]


2. Create the /data Folder

In the main project folder, create a new folder named data.

Place your merged_property_dataset.csv file inside this data folder.

3. Set Up a Virtual Environment

python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS/Linux
source venv/bin/activate


4. Install Dependencies

pip install -r requirements.txt


5. Set Up Your Environment Variables

Create a new file named .env in the root of the project.

Copy the contents of .env.example into it.

Add your Google AI (Gemini) API key to the .env file:

GOOGLE_API_KEY="YOUR_API_KEY_GOES_HERE"


6. Run the Streamlit App

streamlit run app.py


The application should now be running in your web browser!

📂 Final Project Structure

.
├── data/
│   └── merged_property_dataset.csv
├── 📄 .env.example
├── 📄 README.md
├── 📄 app.py
└── 📄 requirements.txt


🧰 Submission Details

GitHub Repository: This repository contains all the necessary code and documentation.

Usernames for Sharing: Prathameshzad, batty-sk
