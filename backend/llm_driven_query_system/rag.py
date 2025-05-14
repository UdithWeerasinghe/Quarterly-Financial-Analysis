"""
rag.py

Implements the Retrieval-Augmented Generation (RAG) pipeline for financial document Q&A.
Combines a vector store for semantic search with a large language model (LLM) for answer generation.

Key Features:
- Loads a vector store of financial document embeddings for fast semantic search.
- Extracts relevant context from search results based on user queries.
- Uses an LLM to generate natural language answers using the retrieved context.
- Handles company, metric, quarter, and year extraction for precise filtering.

Usage:
    from rag import RAGPipeline
    pipeline = RAGPipeline()
    results = pipeline.query("What was DIPD's Revenue in Q3 2022?")

Requirements:
    - faiss, numpy, pandas, langchain, langchain_ollama, requests, pdfplumber
"""

import os
import logging
from pathlib import Path
from backend.llm_driven_query_system.vector_store_creation import create_vector_store
import re

# Set up logging for the RAG pipeline
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class RAGPipeline:
    """
    Retrieval-Augmented Generation pipeline for financial Q&A.
    Combines a vector store for semantic search with an LLM for answer generation.
    """
    def __init__(self):
        """
        Initialize the RAG pipeline with a vector store and LLM.
        Loads the vector store from disk or creates it if necessary.
        """
        try:
            # Get module directory
            MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
            BACKEND_DIR = os.path.dirname(os.path.dirname(MODULE_DIR))
            
            # Define paths relative to backend directory
            pdf_dir = os.path.join(BACKEND_DIR, "data_scraping", "pdfs")
            csv_path = os.path.join(BACKEND_DIR, "dataset_creation", "cleaned_data", "cleaned_quarterly_financials.csv")
            
            # Create or load vector store
            self.vector_store = create_vector_store(
                pdf_dir=pdf_dir,
                csv_path=csv_path,
                force_rebuild=False
            )
            logger.info("RAG pipeline initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing RAG pipeline: {str(e)}")
            raise

    def query(self, question: str, k: int = 10):
        """
        Query the RAG pipeline with a question.
        Args:
            question (str): User's question.
            k (int): Number of top results to retrieve.
        Returns:
            list: List of relevant result dicts.
        """
        try:
            if not question or not isinstance(question, str):
                logger.error("Invalid question format")
                return []

            # Search for relevant documents using the vector store
            results = self.vector_store.search(question, k=k)
            
            if not results:
                logger.info(f"No results found for query: {question}")
                return []
            
            # Extract year, quarter, company, and metric from the question using regex
            year_match = re.search(r'20\d{2}', question)
            year = int(year_match.group()) if year_match else None
            quarter_match = re.search(r'(1st|2nd|3rd|4th|Q[1-4])', question, re.IGNORECASE)
            quarter_map = {'1st': 'Q1', '2nd': 'Q2', '3rd': 'Q3', '4th': 'Q4', 'Q1': 'Q1', 'Q2': 'Q2', 'Q3': 'Q3', 'Q4': 'Q4'}
            quarter = quarter_map[quarter_match.group().capitalize()] if quarter_match else None
            company_match = re.search(r'REXP|DIPD', question, re.IGNORECASE)
            company = company_match.group().upper() if company_match else None
            metric_match = re.search(r'Revenue|COGS|Gross Profit|Operating Expenses|Operating Income|Net Income', question, re.IGNORECASE)
            metric = metric_match.group() if metric_match else None

            # Post-filter for exact match on year, quarter, company, and metric
            filtered = []
            for r in results:
                try:
                    if year and r.get('year') != year:
                        continue
                    if quarter and r.get('quarter') != quarter:
                        continue
                    if company and (not r.get('company') or r.get('company').upper() != company):
                        continue
                    if metric and metric not in r.get('metrics', {}):
                        continue
                    filtered.append(r)
                except Exception as e:
                    logger.error(f"Error processing result: {str(e)}")
                    continue

            # If nothing matches, fall back to original results
            return filtered if filtered else results
        except Exception as e:
            logger.error(f"Error querying RAG pipeline: {str(e)}")
            return []

    def normalize_result(self, result):
        """
        Normalize a result dictionary for API responses.
        Args:
            result (dict): Raw result dict.
        Returns:
            dict: Normalized result dict.
        """
        return {
            "company": result.get('company') or result.get('Company'),
            "date": result.get('date') or result.get('TableDate'),
            "year": result.get('year') or result.get('Year'),
            "quarter": result.get('quarter') or result.get('QuarterName') or result.get('Quarter'),
            "quarter_period": result.get('quarter_period') or result.get('QuarterPeriod'),
            "metrics": result.get('metrics') or {result.get('Metric'): result.get('Value')}
        }

if __name__ == "__main__":
    """
    Test the RAG pipeline with sample questions and print the results.
    """
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

from backend.llm_driven_query_system.rag import RAGPipeline
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

# In API endpoint:
normalized_results = [normalize_result(r) for r in results]
print(normalized_results) 