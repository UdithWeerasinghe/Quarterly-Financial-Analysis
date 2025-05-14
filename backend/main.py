# main.py
# Entry point for running the full financial analysis pipeline or launching the API server.

import os
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from llm_driven_query_system.rag import RAGPipeline

# Set up logging for the main entry point
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Define base paths
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BACKEND_DIR, "dataset_creation", "cleaned_data")
PDF_DIR = os.path.join(BACKEND_DIR, "data_scraping", "pdfs")

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
        rag = RAGPipeline()
        logger.info("RAG pipeline initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing RAG system: {str(e)}")
        raise

@app.post("/api/query", response_model=QueryResponse)
async def query_endpoint(query: Query):
    if not rag:
        raise HTTPException(status_code=500, detail="RAG system not initialized")
    
    try:
        # Get search results
        results = rag.query(query.text, k=query.k)
        
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
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 