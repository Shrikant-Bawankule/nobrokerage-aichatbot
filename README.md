#  NoBrokerage.com — AI-Powered Property Search

> **An intelligent conversational property search assistant built with Streamlit and Google Gemini.** This project demonstrates how natural language queries can be transformed into precise property searches using AI and a local dataset.

---

## 🚀 Live Demo

https://nobrokerage-aichatbot.streamlit.app/

---

## 📘 Project Overview

This project represents an **AI-driven property search assistant** that allows users to interact naturally with the system — as they would with a human agent. It understands follow-up questions, refines previous searches, and displays clean, data-driven results.

### 🔑 Core Functionalities

* **Natural Language Understanding:** Extracts structured search filters from free-form user input (e.g., “2BHK in Pune between 1 and 2 Cr”).
* **Conversational Context Awareness:** Understands follow-up refinements such as “under 3 Cr” after a previous search.
* **Dynamic Data Filtering:** Filters property listings from a local CSV dataset in real-time using Pandas.
* **AI-Generated Summaries:** Uses the Gemini API to summarize the search results with relevant insights.
* **Modern UI:** A responsive and user-friendly Streamlit interface featuring interactive property cards and a sidebar filter system.

---

## ⚙️ Tech Stack

| Layer               | Tool                                 | Justification                                                                                 |
| :------------------ | :----------------------------------- | :-------------------------------------------------------------------------------------------- |
| **Frontend / App**  | Streamlit                            | Enables rapid development of interactive, data-centric web apps in Python.                    |
| **AI / NLP Engine** | Google Gemini API (gemini-2.5-flash) | Advanced large language model capable of understanding and structuring complex human queries. |
| **Data Layer**      | Pandas DataFrame                     | Efficient in-memory data filtering and manipulation for local CSV datasets.                   |
| **Language**        | Python                               | Provides seamless integration between AI, data processing, and UI components.                 |

---

## 🧠 Architecture Overview

1. **User Input:** The user types a query like *“3BHK in Mumbai under 2 Cr”*.
2. **Gemini Processing:** The query is sent to Gemini to extract structured filters such as city, price range, and property type.
3. **Data Filtering:** Pandas applies these filters on the local dataset (`merged_property_dataset.csv`).
4. **AI Summary:** Gemini generates a human-readable summary of the filtered results.
5. **UI Rendering:** Streamlit displays the results as interactive property cards, updating dynamically as queries change.

---

## 📂 Project Structure

```
.
├── data/
│   └── merged_property_dataset.csv
├── .env.example
├── app.py
├── requirements.txt
└── README.md
```

---

## 💻 Setup Instructions

Follow these steps to run the application locally:

### 1️⃣ Clone the Repository

```bash
git clone [your-github-repo-url]
cd [your-repo-name]
```

### 2️⃣ Prepare the Dataset

Create a new folder named `data` in the root directory and place your dataset file inside it:

```
data/
└── merged_property_dataset.csv
```

### 3️⃣ Set Up a Virtual Environment

```bash
python -m venv venv
# On Windows
env\Scripts\activate
# On macOS/Linux
source venv/bin/activate
```

### 4️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

### 5️⃣ Configure Environment Variables

Create a new `.env` file in the project root and add your Google API key:

```env
GOOGLE_API_KEY="YOUR_API_KEY_GOES_HERE"
```

### 6️⃣ Run the Application

```bash
streamlit run app.py
```

Your application will open in the default web browser.

---

## 🧾 Example `.env.example`

```env
# Copy this file to .env and replace with your actual key
GOOGLE_API_KEY="YOUR_API_KEY_GOES_HERE"
# Optional: specify Gemini model
# GEMINI_MODEL="gemini-2.5-flash"
```

---

## 🧩 Example Queries Supported

| User Query                                | AI Interpretation                                      |
| ----------------------------------------- | ------------------------------------------------------ |
| “2BHK in Pune between 60L and 1.2Cr”      | City = Pune, Bedrooms = 2, Price Range = 60L–1.2Cr     |
| “Flats in Mumbai under 3Cr near Andheri”  | City = Mumbai, Locality = Andheri, Max Price = 3Cr     |
| Follow-up: “Show only ready-to-move ones” | Adds possession_status = Ready to Move                 |

---

## 🧠 AI Workflow Summary

1. Gemini model extracts structured filters from natural language.
2. Filters are validated and applied to the Pandas DataFrame.
3. Matching results are displayed via Streamlit cards.
4. Gemini generates a concise summary (e.g., pricing trends, key localities).

---

## 🧭 Deployment Notes

* Deployed on **Streamlit Cloud**
* Ensure `.env` variables are properly configured using platform secrets.
* Keep the dataset lightweight for fast filtering performance.


<img width="1919" height="969" alt="image" src="https://github.com/user-attachments/assets/8d1ee8d0-8f36-46ba-8b60-7be54076cdfc" />

---

## 🔒 Privacy & Ethical Use

* The app only processes local CSV data. No personal user data is stored.
* Gemini is used for understanding queries and summarizing results, not for storing or tracking data.
* Summaries are generated responsibly without exposing internal dataset statistics.

---

## 📈 Future Enhancements

* Add geolocation-based search (distance filters)
* Implement caching for faster query responses
* Allow export of shortlisted properties as CSV or PDF
* Integrate authentication for personalized experiences

---


## 🏁 Conclusion

The **NoBrokerage.com AI-Powered Property Search** is a proof-of-concept that integrates AI, data analysis, and modern UI frameworks to revolutionize how users explore real estate listings. By combining **Google Gemini’s conversational intelligence** with **Streamlit’s interactivity**, this project demonstrates how data-driven, user-friendly applications can deliver smart, human-like search experiences.

