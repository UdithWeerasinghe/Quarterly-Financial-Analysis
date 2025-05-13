import os
import pandas as pd
import numpy as np
import faiss
from pathlib import Path
import logging
import pdfplumber
import re
from datetime import datetime
from sentence_transformers import SentenceTransformer
import pickle

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FinancialVectorStore:
    def __init__(self, model_name="FinLang/finance-embeddings-investopedia"):
        """Initialize the vector store with SentenceTransformers."""
        try:
            self.model = SentenceTransformer(model_name)
            self.embedding_dimension = self.model.get_sentence_embedding_dimension()
            logger.info(f"Using SentenceTransformer model: {model_name} (dim={self.embedding_dimension})")
            # Initialize FAISS index
            self.index = faiss.IndexFlatL2(self.embedding_dimension)
            # Store metadata
            self.metadata = []
            
            # Get module directory for embeddings
            MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
            self.embeddings_dir = os.path.join(MODULE_DIR, "embeddings")
            os.makedirs(self.embeddings_dir, exist_ok=True)
        except Exception as e:
            logger.error(f"Error initializing vector store: {str(e)}")
            raise

    def save(self, index_path=None, metadata_path=None):
        """Save the FAISS index and metadata to disk."""
        try:
            if index_path is None:
                index_path = os.path.join(self.embeddings_dir, "faiss_index.bin")
            if metadata_path is None:
                metadata_path = os.path.join(self.embeddings_dir, "faiss_metadata.pkl")
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(index_path), exist_ok=True)
            
            # Save FAISS index
            faiss.write_index(self.index, index_path)
            logger.info(f"Saved FAISS index to {index_path}")
            
            # Save metadata
            with open(metadata_path, 'wb') as f:
                pickle.dump(self.metadata, f)
            logger.info(f"Saved metadata to {metadata_path}")
            
            return True
        except Exception as e:
            logger.error(f"Error saving vector store: {str(e)}")
            return False

    def load(self, index_path=None, metadata_path=None):
        """Load the FAISS index and metadata from disk."""
        try:
            if index_path is None:
                index_path = os.path.join(self.embeddings_dir, "faiss_index.bin")
            if metadata_path is None:
                metadata_path = os.path.join(self.embeddings_dir, "faiss_metadata.pkl")
            
            if not os.path.exists(index_path) or not os.path.exists(metadata_path):
                logger.warning("No existing vector store found. Creating new one.")
                return False
            
            # Load FAISS index
            self.index = faiss.read_index(index_path)
            logger.info(f"Loaded FAISS index from {index_path}")
            
            # Load metadata
            with open(metadata_path, 'rb') as f:
                self.metadata = pickle.load(f)
            logger.info(f"Loaded metadata from {metadata_path}")
            
            return True
        except Exception as e:
            logger.error(f"Error loading vector store: {str(e)}")
            return False

    def get_embedding(self, text):
        """Get embedding from SentenceTransformers."""
        try:
            return self.model.encode([text])[0]
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
                    if embedding is not None:
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
        """Create embeddings from CSV data, one per metric per row."""
        logger.info("Creating embeddings from CSV...")
        financial_metrics = ['Revenue', 'COGS', 'Gross Profit', 'Operating Expenses', 'Operating Income', 'Net Income']
        try:
            df = pd.read_csv(csv_path, parse_dates=["TableDate"])
            all_texts = []
            all_metadata = []
            
            for idx, row in df.iterrows():
                # Extract quarter information
                date = pd.to_datetime(row['TableDate'])
                month = date.month
                
                # Define quarters based on month
                if month in [3, 6, 9, 12]:  # Quarter end months
                    quarter = (month // 3)
                    quarter_name = f"Q{quarter}"
                    quarter_period = {
                        3: "Q1 (January to March)",
                        6: "Q2 (April to June)",
                        9: "Q3 (July to September)",
                        12: "Q4 (October to December)"
                    }[month]
                else:
                    continue  # Skip non-quarter-end dates
                
                year = date.year
                
                for metric in financial_metrics:
                    if metric in row:
                        value = row[metric]
                        text = (
                            f"Company: {row['Company']}\n"
                            f"Metric: {metric}\n"
                            f"Date: {date.strftime('%Y-%m-%d')}\n"
                            f"Year: {year}\n"
                            f"Quarter: {quarter_name}\n"
                            f"Quarter Period: {quarter_period}\n"
                            f"Value: {value:,.2f} LKR\n"
                            f"Note: All values are in Sri Lankan Rupees (LKR), and are in thousands."
                        )
                        all_texts.append(text)
                        all_metadata.append({
                            "Company": row['Company'],
                            "Metric": metric,
                            "TableDate": row['TableDate'],
                            "Year": year,
                            "Quarter": quarter,
                            "QuarterName": quarter_name,
                            "QuarterPeriod": quarter_period,
                            "Value": value,
                            "RowIdx": idx
                        })
            
            # Create embeddings
            embeddings = []
            for i, text in enumerate(all_texts):
                if i % 10 == 0:
                    logger.info(f"Processing metric chunk {i+1}/{len(all_texts)}")
                embedding = self.get_embedding(text)
                if embedding is not None:
                    embeddings.append(embedding)
                else:
                    logger.warning(f"Failed to get embedding for metric chunk {i+1}")
            
            if embeddings:
                self.index.add(np.array(embeddings).astype('float32'))
                self.metadata.extend(all_metadata)
                logger.info(f"Created {len(embeddings)} metric-specific embeddings from CSV")
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

def create_vector_store(pdf_dir=None, csv_path=None, force_rebuild=False):
    """Create and return a vector store from PDF and/or CSV data."""
    try:
        vector_store = FinancialVectorStore()
        
        # Try to load existing vector store
        if not force_rebuild and vector_store.load():
            logger.info("Successfully loaded existing vector store")
            return vector_store
        
        # If loading failed or force_rebuild is True, create new vector store
        logger.info("Creating new vector store...")
        if pdf_dir:
            vector_store.create_embeddings_from_pdfs(pdf_dir)
        if csv_path:
            vector_store.create_embeddings_from_csv(csv_path)
        
        # Save the newly created vector store
        vector_store.save()
        
        return vector_store
    except Exception as e:
        logger.error(f"Error creating vector store: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        # Test the vector store
        pdf_dir = Path("backend/data_scraping/pdfs")
        csv_path = Path("backend/dataset_creation/cleaned_data/cleaned_quarterly_financials.csv")
        logger.info("Initializing vector store...")
        
        # Create or load vector store
        vector_store = create_vector_store(pdf_dir=pdf_dir, csv_path=csv_path)
        
        # Test search
        test_queries = [
            "What was DIPD's Revenue in the last quarter?",
            "Show me the Gross Profit for REXP",
            "Compare Operating Income between DIPD and REXP"
        ]
        for query in test_queries:
            logger.info(f"\nTesting query: {query}")
            results = vector_store.search(query)
            print(f"\nResults for query: {query}")
            for result in results:
                print(f"\nCompany: {result.get('Company', 'N/A')}")
                print(f"Date: {result.get('TableDate', 'N/A')}")
                # Print all available financial metrics for this result
                for metric in ['Revenue', 'COGS', 'Gross Profit', 'Operating Expenses', 'Operating Income', 'Net Income']:
                    if metric in result:
                        print(f"{metric}: {result[metric]:,.2f} LKR")
                print(f"Similarity Score: {result.get('similarity_score', 0):.2f}")
    except Exception as e:
        logger.error(f"Error in main: {str(e)}") 