# Quarterly Financial Analysis

A comprehensive solution for analyzing quarterly financial reports of companies listed on the Colombo Stock Exchange (CSE).

## Features

- Automated scraping of quarterly financial reports
- Data extraction and processing
- Interactive dashboard for data visualization
- Natural language querying of financial data using LLMs
- Comparative analysis between companies

## Project Structure

```
.
├── backend/
│   ├── src/
│   │   ├── scraper.py      # Web scraping module
│   │   ├── parser.py       # PDF parsing and data extraction
│   │   ├── dashboard.py    # Interactive dashboard
│   │   └── llm_query.py    # LLM-based query system
│   ├── app.py             # FastAPI application
│   ├── main.py            # Main application script
│   └── requirements.txt   # Python dependencies
├── data/                  # Downloaded PDF reports
├── output/               # Processed data files
└── README.md            # This file
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
