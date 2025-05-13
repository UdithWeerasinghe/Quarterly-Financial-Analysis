import pandas as pd
import numpy as np
import faiss
import torch
from pathlib import Path
import logging
import pdfplumber
import re
from datetime import datetime
import os
import requests
import json

# Set up logging with more detail
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FinancialVectorStore:
    def __init__(self, model_name="llama2"):
        """Initialize the vector store with Ollama."""
        try:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Using device: {self.device}")
            
            # Initialize Ollama client
            self.model_name = model_name
            self.ollama_url = "http://localhost:11434/api/embeddings"
            logger.info(f"Using Ollama model: {model_name}")
            
            # Test Ollama connection
            try:
                response = requests.post(
                    self.ollama_url,
                    json={"model": self.model_name, "prompt": "test"}
                )
                if response.status_code != 200:
                    raise Exception(f"Ollama API returned status code {response.status_code}")
                self.embedding_dimension = len(response.json()["embedding"])
                logger.info(f"Successfully connected to Ollama. Embedding dimension: {self.embedding_dimension}")
            except Exception as e:
                logger.error(f"Failed to connect to Ollama: {str(e)}")
                raise
            
            # Initialize FAISS index
            self.index = faiss.IndexFlatL2(self.embedding_dimension)
            
            # Store metadata
            self.metadata = []
            
        except Exception as e:
            logger.error(f"Error initializing vector store: {str(e)}")
            raise

    def get_embedding(self, text):
        """Get embedding from Ollama."""
        try:
            response = requests.post(
                self.ollama_url,
                json={"model": self.model_name, "prompt": text}
            )
            if response.status_code == 200:
                return response.json()["embedding"]
            else:
                logger.error(f"Ollama API error: {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error getting embedding: {str(e)}")
            return None

    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF and split into chunks."""
        chunks = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        # Split text into smaller chunks (e.g., by paragraphs)
                        paragraphs = text.split('\n\n')
                        for para in paragraphs:
                            if len(para.strip()) > 50:  # Only keep substantial chunks
                                chunks.append(para.strip())
        except Exception as e:
            logger.error(f"Error processing {pdf_path}: {str(e)}")
        return chunks

    def prepare_text(self, text, metadata=None):
        """Prepare text for embedding."""
        if metadata:
            return f"""
            Company: {metadata.get('Company', 'N/A')}
            Date: {metadata.get('Date', 'N/A')}
            Report: {metadata.get('ReportName', 'N/A')}
            Content: {text}
            """.strip()
        return text.strip()
    
    def create_embeddings_from_pdfs(self, pdf_dir):
        """Create embeddings from PDF files."""
        logger.info("Creating embeddings from PDFs...")
        
        pdf_dir = Path(pdf_dir)
        if not pdf_dir.exists():
            logger.error(f"PDF directory not found: {pdf_dir}")
            return
        
        all_texts = []
        all_metadata = []
        
        # Process each PDF file
        for pdf_file in pdf_dir.glob("**/*.pdf"):  # Changed to recursive search
            logger.info(f"Processing {pdf_file.name}")
            
            # Extract company name from directory structure
            company = pdf_file.parent.name
            date = pdf_file.stem.split('_')[0] if '_' in pdf_file.stem else "Unknown"
            
            # Extract text chunks from PDF
            chunks = self.extract_text_from_pdf(pdf_file)
            
            # Prepare metadata for each chunk
            for chunk in chunks:
                metadata = {
                    'Company': company,
                    'Date': date,
                    'ReportName': pdf_file.name,
                    'Source': 'PDF'
                }
                all_texts.append(self.prepare_text(chunk, metadata))
                all_metadata.append(metadata)
        
        if all_texts:
            try:
                # Create embeddings
                logger.info(f"Creating embeddings for {len(all_texts)} chunks...")
                embeddings = []
                for i, text in enumerate(all_texts):
                    if i % 10 == 0:  # Log progress every 10 chunks
                        logger.info(f"Processing chunk {i+1}/{len(all_texts)}")
                    embedding = self.get_embedding(text)
                    if embedding:
                        embeddings.append(embedding)
                    else:
                        logger.warning(f"Failed to get embedding for chunk {i+1}")
                
                if embeddings:
                    # Add to FAISS index
                    self.index.add(np.array(embeddings).astype('float32'))
                    
                    # Store metadata
                    self.metadata.extend(all_metadata)
                    
                    logger.info(f"Created {len(embeddings)} embeddings from PDFs")
                else:
                    logger.error("No embeddings were created successfully")
            except Exception as e:
                logger.error(f"Error creating embeddings: {str(e)}")
        else:
            logger.warning("No text chunks extracted from PDFs")
    
    def create_embeddings_from_csv(self, csv_path):
        """Create embeddings from CSV data."""
        logger.info("Creating embeddings from CSV...")
        
        try:
            df = pd.read_csv(csv_path, parse_dates=["TableDate"])
            
            # Prepare texts
            texts = [self.prepare_text(row) for _, row in df.iterrows()]
            
            # Create embeddings
            embeddings = []
            for i, text in enumerate(texts):
                if i % 10 == 0:  # Log progress every 10 rows
                    logger.info(f"Processing row {i+1}/{len(texts)}")
                embedding = self.get_embedding(text)
                if embedding:
                    embeddings.append(embedding)
                else:
                    logger.warning(f"Failed to get embedding for row {i+1}")
            
            if embeddings:
                # Add to FAISS index
                self.index.add(np.array(embeddings).astype('float32'))
                
                # Store metadata
                self.metadata.extend(df.to_dict('records'))
                
                logger.info(f"Created {len(embeddings)} embeddings from CSV")
            else:
                logger.error("No embeddings were created successfully")
        except Exception as e:
            logger.error(f"Error processing CSV: {str(e)}")
    
    def search(self, query, k=5):
        """Search for similar financial records."""
        try:
            # Create query embedding
            query_embedding = self.get_embedding(query)
            if query_embedding is None:
                logger.error("Failed to get query embedding")
                return []
            
            # Search in FAISS
            distances, indices = self.index.search(
                np.array([query_embedding]).astype('float32'), k
            )
            
            # Return results with metadata
            results = []
            for idx, distance in zip(indices[0], distances[0]):
                if idx != -1:  # FAISS returns -1 for empty slots
                    result = self.metadata[idx].copy()
                    result['similarity_score'] = float(1 / (1 + distance))
                    results.append(result)
            
            return results
        except Exception as e:
            logger.error(f"Error during search: {str(e)}")
            return []

def create_vector_store(pdf_dir=None, csv_path=None):
    """Create and return a vector store from PDF and/or CSV data."""
    try:
        vector_store = FinancialVectorStore()
        
        if pdf_dir:
            vector_store.create_embeddings_from_pdfs(pdf_dir)
        
        if csv_path:
            vector_store.create_embeddings_from_csv(csv_path)
        
        return vector_store
    except Exception as e:
        logger.error(f"Error creating vector store: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        # Test the vector store
        pdf_dir = Path("backend/data_collection/downloaded_pdfs")
        csv_path = Path("backend/data_collection/quarterly_financials.csv")
        
        logger.info("Initializing vector store...")
        vector_store = create_vector_store(pdf_dir=pdf_dir, csv_path=csv_path)
        
        # Test search
        test_queries = [
            "Show me the latest financial performance of Dipped Products",
            "What was the revenue growth in the last quarter?",
            "Compare the operating income between DIPD and REXP"
        ]
        
        for query in test_queries:
            logger.info(f"\nTesting query: {query}")
            results = vector_store.search(query)
            
            print(f"\nResults for query: {query}")
            for result in results:
                print(f"\nCompany: {result['Company']}")
                print(f"Date: {result['Date']}")
                print(f"Report: {result['ReportName']}")
                print(f"Similarity Score: {result['similarity_score']:.2f}")
    except Exception as e:
        logger.error(f"Error in main: {str(e)}") 