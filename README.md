# Quarterly Financial Analysis

## Overview

This project provides a modular pipeline for extracting, cleaning, analyzing, visualizing, and interactively querying quarterly financial data from companies listed on the Colombo Stock Exchange (CSE). It supports both dashboard-based exploration and LLM-powered conversational Q&A, using a finance-specific embedding model and a Flask-based API.

---

## Table of Contents

1. [Project Structure](#project-structure)
2. [Setup and Installation](#setup-and-installation)
3. [Running the Application](#running-the-application)
4. [Usage](#usage)
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
```

## Setup and Installation

### Virtual Environment Setup

1. Create a virtual environment:

```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On Linux/Mac
python -m venv venv
source venv/bin/activate
```

### Backend Setup

1. Install Python dependencies:

```bash
pip install -r requirements.txt
```

### Ollama Setup (for LLM)

1. [Install Ollama](https://ollama.com/download) (local LLM server)
2. Download and run the model:

```bash
ollama pull llama3.2:3b
ollama serve
```

### Frontend Setup

1. Navigate to the frontend directory:

```bash
cd frontend
```

2. Install Node.js dependencies:

```bash
npm install
```

## Running the Application

### Backend Pipeline

Run the following commands in sequence from the root directory:

1. Scrape financial data:

```bash
python backend/data_scraping/cse_scraper.py
```

2. Extract tables from PDFs:

```bash
python backend/dataset_creation/extract_tables.py
```

3. Preprocess the extracted data:

```bash
python backend/dataset_creation/preprocessing.py
```

4. Create vector store for LLM:

```bash
python backend/llm_driven_query_system/vector_store_creation.py
```

5. Initialize RAG pipeline:

```bash
python backend/llm_driven_query_system/rag.py
```

6. Start the Flask server:

```bash
python backend/app.py
```

### Frontend

1. Navigate to the frontend directory:

```bash
cd frontend
```

2. Start the React development server:

```bash
npm start
```

The application should now be running with:

- Backend API at: http://localhost:5000
- Frontend at: http://localhost:3000

## Usage

### Dashboard

Access the interactive dashboard at `http://localhost:3000` to:

- View financial metrics over time
- Compare companies
- Analyze trends
- View key financial ratios

### Query System

Send natural language queries to the API endpoint:

```bash
curl -X POST "http://localhost:5000/api/query" \
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

## Configuration

- **`scraper_config.yaml`:** Add or update companies, report patterns, and keywords
- **Preprocessing:** Update `preprocessor.py` for new metrics or data formats
- **Embedding Model:** Uses `FinLang/finance-embeddings-investopedia`
- **LLM Model:** Ollama runs `llama3.2:3b` (configurable in `app.py`)

## Key Features

- Modular, config-driven pipeline
- Robust PDF scraping and table extraction
- Automated data cleaning and validation
- Finance-specific semantic search and LLM Q&A
- Interactive dashboard and chat interface
- Extensible to new companies, metrics, and years

## Troubleshooting & FAQ

- **No PDFs downloaded?** Check `scraper_config.yaml` and CSE website structure
- **Table extraction fails?** Check logs in `extract_tables.log`
- **Ollama errors?** Ensure Ollama is running and model is downloaded
- **API not responding?** Check Flask logs and dependencies
- **Frontend not connecting?** Ensure backend API is running and CORS is enabled

## Credits

- **Developed by:** Udith Weerasinghe
- **Data Source:** Colombo Stock Exchange (CSE)
- **LLM:** [Ollama](https://ollama.com/) with `llama3.2:3b`
- **Embeddings:** [FinLang/finance-embeddings-investopedia](https://huggingface.co/FinLang/finance-embeddings-investopedia)
- **Libraries:** Flask, pandas, pdfplumber, sentence-transformers, faiss, React, Chart.js, etc.

---

**For any issues or contributions, please open an issue or pull request on this repository.**
