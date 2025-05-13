import os
import json
import logging
from pathlib import Path
import faiss
import numpy as np
import requests
from langchain_ollama.llms import OllamaLLM
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import pandas as pd
import pdfplumber
import pickle
from vector_store import create_vector_store
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RAGPipeline:
    def __init__(self):
        """Initialize the RAG pipeline with a vector store."""
        try:
            # Create or load vector store
            self.vector_store = create_vector_store(
                pdf_dir="backend/data_collection/downloaded_pdfs",
                csv_path="backend/data_collection/quarterly_financials_cleaned.csv"
            )
            logger.info("RAG pipeline initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing RAG pipeline: {str(e)}")
            raise

    def query(self, question: str, k: int = 10):
        """Query the RAG pipeline with a question."""
        try:
            # Search for relevant documents
            results = self.vector_store.search(question, k=k)
            
            # Try to extract year, quarter, company, and metric from the question
            year_match = re.search(r'20\\d{2}', question)
            year = int(year_match.group()) if year_match else None
            quarter_match = re.search(r'(1st|2nd|3rd|4th|Q[1-4])', question, re.IGNORECASE)
            quarter_map = {'1st': 'Q1', '2nd': 'Q2', '3rd': 'Q3', '4th': 'Q4', 'Q1': 'Q1', 'Q2': 'Q2', 'Q3': 'Q3', 'Q4': 'Q4'}
            quarter = quarter_map[quarter_match.group().capitalize()] if quarter_match else None
            company_match = re.search(r'REXP|DIPD', question, re.IGNORECASE)
            company = company_match.group().upper() if company_match else None
            metric_match = re.search(r'Revenue|COGS|Gross Profit|Operating Expenses|Operating Income|Net Income', question, re.IGNORECASE)
            metric = metric_match.group() if metric_match else None

            # Post-filter for exact match
            filtered = []
            for r in results:
                if year and r.get('year') != year:
                    continue
                if quarter and r.get('quarter') != quarter:
                    continue
                if company and (not r.get('company') or r.get('company').upper() != company):
                    continue
                if metric and metric not in r['metrics']:
                    continue
                filtered.append(r)
            # If nothing matches, fall back to original results
            return filtered if filtered else results
        except Exception as e:
            logger.error(f"Error querying RAG pipeline: {str(e)}")
            return []

    def normalize_result(self, result):
        return {
            "company": result.get('company') or result.get('Company'),
            "date": result.get('date') or result.get('TableDate'),
            "year": result.get('year') or result.get('Year'),
            "quarter": result.get('quarter') or result.get('QuarterName') or result.get('Quarter'),
            "quarter_period": result.get('quarter_period') or result.get('QuarterPeriod'),
            "metrics": result.get('metrics') or {result.get('Metric'): result.get('Value')}
        }

if __name__ == "__main__":
    # Test the RAG pipeline
    try:
        pipeline = RAGPipeline()
        test_questions = [
            "What was DIPD's Revenue in the last quarter?",
            "Show me the Gross Profit for REXP",
            "Compare Operating Income between DIPD and REXP",
            "What is the revenue of the 3rd quarter of 2022 for REXP"
        ]
        
        for question in test_questions:
            print(f"\nQuestion: {question}")
            results = pipeline.query(question)
            for result in results:
                company = result.get('company') or result.get('Company')
                date = result.get('date') or result.get('TableDate')
                print(f"\nCompany: {company}")
                print(f"Date: {date}")
                for metric, value in (result.get('metrics') or {result.get('Metric'): result.get('Value')}).items():
                    print(f"{metric}: {value:,.2f} LKR")
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")

from rag_pipeline import RAGPipeline
pipeline = RAGPipeline()
results = pipeline.query("What is the revenue of the 3rd quarter of 2022 for REXP?")
print(results)

def normalize_result(result):
    return {
        "company": result.get('company') or result.get('Company'),
        "date": result.get('date') or result.get('TableDate'),
        "year": result.get('year') or result.get('Year'),
        "quarter": result.get('quarter') or result.get('QuarterName') or result.get('Quarter'),
        "quarter_period": result.get('quarter_period') or result.get('QuarterPeriod'),
        "metrics": result.get('metrics') or {result.get('Metric'): result.get('Value')}
    }

# In your API endpoint:
normalized_results = [normalize_result(r) for r in results]
print(normalized_results) 