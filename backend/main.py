import os
import logging
from src.scraper import CSEScraper
from src.parser import FinancialDataParser
from src.dashboard import FinancialDashboard
from src.llm_query import FinancialQueryEngine
import uvicorn
from app import app
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from rag_pipeline import FinancialRAG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_directories():
    """Create necessary directories if they don't exist."""
    directories = ['data', 'output']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def scrape_and_process_data():
    """Scrape and process financial data for all companies."""
    try:
        # Initialize scraper and parser
        scraper = CSEScraper()
        parser = FinancialDataParser()
        
        # Process each company
        data_dict = {}
        for symbol in ["DIPD", "REXP"]:
            logger.info(f"Processing {symbol}...")
            
            # Get reports
            reports = scraper.get_company_reports(symbol)
            
            # Process each report
            parsed_data = []
            for report in reports:
                # Download report
                save_path = f"data/{symbol}/{report['date'].strftime('%Y%m%d')}.pdf"
                if scraper.download_report(report['url'], save_path):
                    # Extract data from PDF
                    text = scraper.extract_financial_data(save_path)
                    if text:
                        # Parse financial data
                        data = parser.parse_financial_data(text, report['date'])
                        if data:
                            parsed_data.append(data)
            
            # Create DataFrame
            if parsed_data:
                df = parser.create_dataframe(parsed_data)
                data_dict[symbol] = df
                
                # Save to CSV
                df.to_csv(f"output/{symbol}_financials.csv")
        
        return data_dict
    except Exception as e:
        logger.error(f"Error in scrape_and_process_data: {str(e)}")
        return None

def main():
    """Main function to run the application."""
    try:
        # Setup directories
        setup_directories()
        
        # Scrape and process data
        data_dict = scrape_and_process_data()
        if not data_dict:
            logger.error("Failed to process data")
            return
        
        # Initialize dashboard
        dashboard = FinancialDashboard(data_dict)
        
        # Initialize query engine
        query_engine = FinancialQueryEngine(data_dict)
        
        # Run FastAPI server
        uvicorn.run(app, host="0.0.0.0", port=8000)
        
        # Run dashboard server
        dashboard.run_server(port=8050)
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG system
rag = None

class Query(BaseModel):
    text: str
    k: Optional[int] = 3

class QueryResponse(BaseModel):
    response: str
    sources: List[dict]

@app.on_event("startup")
async def startup_event():
    global rag
    try:
        rag = FinancialRAG()
        # Build indices
        pdf_dir = "backend/data_collection/downloaded_pdfs"
        csv_path = "backend/data_collection/quarterly_financials_cleaned.csv"
        
        if rag.build_index_from_pdfs(pdf_dir):
            logger.info("Successfully built PDF index")
        if rag.build_index_from_csv(csv_path):
            logger.info("Successfully built CSV index")
    except Exception as e:
        logger.error(f"Error initializing RAG system: {str(e)}")
        raise

@app.post("/api/query", response_model=QueryResponse)
async def query_endpoint(query: Query):
    if not rag:
        raise HTTPException(status_code=500, detail="RAG system not initialized")
    
    try:
        # Get search results
        results = rag.search(query.text, k=query.k)
        
        if not results:
            return QueryResponse(
                response="I couldn't find any relevant information to answer your question.",
                sources=[]
            )
        
        # Prepare context from results
        context = "\n\n".join([
            f"Document {i+1}:\n{result['text']}\nRelevance: {result['similarity_score']:.2f}"
            for i, result in enumerate(results)
        ])
        
        # Generate response
        response = rag.generate_response(query.text, context)
        
        # Prepare sources
        sources = [
            {
                "text": result["text"],
                "metadata": result["metadata"],
                "relevance": result["similarity_score"]
            }
            for result in results
        ]
        
        return QueryResponse(response=response, sources=sources)
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    main() 