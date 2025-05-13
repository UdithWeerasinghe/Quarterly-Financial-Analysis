# Quarterly Financial Analysis

## Overview

This project provides a modular pipeline for extracting, cleaning, analyzing, visualizing, and interactively querying quarterly financial data from companies listed on the Colombo Stock Exchange (CSE). It supports both dashboard-based exploration and LLM-powered conversational Q&A, using a finance-specific embedding model and a Flask-based API.

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Environment Setup](#environment-setup)
3. [Step-by-Step Usage](#step-by-step-usage)
4. [Frontend Dashboard & Chatbot](#frontend-dashboard--chatbot)
5. [Configuration](#configuration)
6. [Key Features](#key-features)
7. [Troubleshooting & FAQ](#troubleshooting--faq)
8. [Credits](#credits)

---

## Project Structure

```
QUARTERLY-FINANCIAL-ANALYSIS
├── backend/
│   ├── app.py
│   ├── main.py
│   ├── requirements.txt
│   ├── data_scraping/
│   │   ├── cse_scraper.py
│   │   ├── scraper_config.yaml
│   │   └── pdfs/
│   │       ├── REXP/
│   │       └── DIPD/
│   ├── dataset_creation/
│   │   ├── extract_tables.py
│   │   ├── preprocessing.py
│   │   ├── extracted_tables/
│   │   │   └── extracted_quarterly_financials.csv
│   │   └── cleaned_data/
│   │       └── cleaned_quarterly_financials.csv
│   └── llm_driven_query_system/
│       ├── rag.py
│       ├── vector_store_creation.py
│       └── embeddings/
│           ├── faiss_index.bin
│           └── faiss_metadata.pkl
├── frontend/
├── package.json
├── package-lock.json
├── public/
├── node_modules/
└── src/
    ├── App.js
    ├── index.js
    ├── reportWebVitals.js
    ├── api/
    ├── utils/
    └── components/
        ├── DrilldownModal.js
        ├── ExportBar.js
        ├── AIInsights/
        ├── Chat/
        │   └── ChatInterface.js
        ├── Comparisons/
        ├── Layout/
        ├── Metrics/
        │   ├── MetricsChart.js
        │   ├── MetricsTab.js
        │   └── TimeRangeSlider.js
        └── Ratios/
│
└── README.md
```

## Setup Instructions

1. Create a virtual environment:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:

   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python main.py
   ```

The application will:

- Scrape quarterly reports from CSE
- Process and extract financial data
- Start the FastAPI server on port 8000
- Start the dashboard server on port 8050

## Usage

### Dashboard

Access the interactive dashboard at `http://localhost:8050` to:

- View financial metrics over time
- Compare companies
- Analyze trends
- View key financial ratios

### Query System

Send natural language queries to the API endpoint:

```bash
curl -X POST "http://localhost:8000/api/query" \
     -H "Content-Type: application/json" \
     -d '{"question": "What was the revenue growth for DIPD in the last quarter?"}'
```

## Supported Companies

- Dipped Products PLC (DIPD)
- Richard Pieris Exports PLC (REXP)

## Data Points

The system extracts and analyzes the following financial metrics:

- Revenue
- Cost of Goods Sold (COGS)
- Gross Profit
- Operating Expenses
- Operating Income
- Net Income

## Limitations

- The scraper is designed for the current CSE website structure
- PDF parsing accuracy depends on the consistency of report formats
- LLM responses are based on the available financial data

## Contributing

Feel free to submit issues and enhancement requests!

---

## Environment Setup

### 1. Python Environment

- Python 3.9+ recommended.
- Create and activate a virtual environment:
  ```bash
  python -m venv venv
  source venv/bin/activate  # On Windows: venv\Scripts\activate
  ```

### 2. Install Python Dependencies

Navigate to `backend/` and install requirements:

```bash
cd backend
pip install -r requirements.txt
```

**Example `requirements.txt`:**

```
requests
beautifulsoup4
pyyaml
pdfplumber
pandas
numpy
faiss-cpu
sentence-transformers
flask
flask-cors
langchain
langgraph
ollama
```

### 3. Ollama Setup (for LLM)

- [Install Ollama](https://ollama.com/download) (local LLM server).
- Download and run the model used in this project (e.g., `llama3.2:3b`):
  ```bash
  ollama pull llama3.2:3b
  ollama serve
  ```
- Ensure Ollama is running before starting the backend API.

### 4. (Optional) Frontend Setup

If you have a frontend (e.g., React):

```bash
cd frontend
npm install
npm start
```

---

## Step-by-Step Usage

### 1. Scrape Quarterly Report PDFs

```bash
python backend/data_scraping/cse_scraper.py
```

- Downloads PDFs to `backend/data_scraping/pdfs/{COMPANY}/`

### 2. Extract Tables from PDFs

```bash
python backend/dataset_creation/extract_tables.py
```

- Extracts tables to `backend/dataset_creation/extracted_tables/`

### 3. Preprocess and Clean Data

```bash
python backend/dataset_creation/preprocessing.py
```

- Cleans and merges data to `backend/dataset_creation/cleaned_data/final_cleaned.csv`

### 4. Build the Vector Store

```bash
python backend/llm_driven_query_system/vector_store.py
```

- Builds FAISS index and metadata in `backend/llm_driven_query_system/embeddings/`

### 5. Start the Chat API

```bash
python backend/app.py
```

- Starts the Flask API at `http://localhost:5000/api/query`

### 6. (Optional) Access the Dashboard

- Start your frontend (see above).
- Access via `http://localhost:3000` (or your configured port).

---

## Frontend Dashboard & Chatbot

- **Dashboard:**  
  Visualizes trends, comparisons, and allows data exploration.
- **Chatbot:**  
  Users can ask questions like:
  - "What was DIPD's net income in Q2 2023?"
  - "Compare the revenue of REXP and DIPD for the last quarter."
  - "What about the next quarter?"
- **Features:**
  - Contextual, data-driven answers
  - Follow-up questions and clarification
  - Error handling and suggestions

---

## Configuration

- **`scraper_config.yaml`:**  
  Add or update companies, report patterns, and keywords for table extraction.
- **Preprocessing:**  
  Update `preprocessor.py` to handle new metrics or data formats as needed.
- **Embedding Model:**  
  The vector store uses `FinLang/finance-embeddings-investopedia` for finance-specific embeddings.
- **LLM Model:**  
  Ollama runs `llama3.2:3b` (can be changed in `app.py`).

---

## Key Features

- Modular, config-driven pipeline
- Robust PDF scraping and table extraction
- Automated data cleaning and validation
- Finance-specific semantic search and LLM Q&A
- Interactive dashboard and chat interface
- Extensible to new companies, metrics, and years

---

## Troubleshooting & FAQ

- **No PDFs downloaded?**
  - Check `scraper_config.yaml` patterns and the CSE website structure.
- **Table extraction fails?**
  - Check logs in `extract_tables.log` and review problematic PDFs.
- **Ollama errors?**
  - Ensure Ollama is running and the model is downloaded.
- **API not responding?**
  - Check Flask logs and ensure all dependencies are installed.
- **Frontend not connecting?**
  - Ensure the backend API is running and CORS is enabled.

---

## Credits

- **Developed by:** Udith Weerasinghe
- **Data Source:** Colombo Stock Exchange (CSE)
- **LLM:** [Ollama](https://ollama.com/) with `llama3.2:3b`
- **Embeddings:** [FinLang/finance-embeddings-investopedia](https://huggingface.co/FinLang/finance-embeddings-investopedia)
- **Libraries:** Flask, pandas, pdfplumber, sentence-transformers, faiss, React, Chart.js, etc.

---

**For any issues or contributions, please open an issue or pull request on this repository.**
